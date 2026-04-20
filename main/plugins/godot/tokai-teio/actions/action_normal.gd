# action_normal.gd — 待机动作：尾巴自然摇摆
#
# 行为随机切换（每次从 IDLE 唤醒时决定）：
#   SINGLE       50% — 向一侧摆一次，回中，等待 2.5-5s
#   ALTERNATE    30% — 连续左右交替摆 2-4 次，完成后等待 3-6s
#   DELAYED_PAIR 20% — 摆向一侧，停 2-5s，再摆向另一侧，回 IDLE
#
# 单次摆动曲线：
#   上抬 (T_LIFT=0.22s)：sin(s·π/2) — 快起慢收，像被轻弹
#   下落 (T_FALL=0.50s)：cos(s·π/2) — 摆锤 SHM 精确解，顶慢底快，模拟重力感
#   骨链相位延迟：根骨先动，末骨依次跟随

func play(c: Node3D, on_finish: Callable) -> Tween:
	var sk: Skeleton3D = c._skeleton
	if sk == null:
		var tw := c.create_tween()
		tw.tween_interval(0.01)
		tw.finished.connect(on_finish, CONNECT_ONE_SHOT)
		return tw

	# ── 骨骼初始化 ──────────────────────────────────────────────────
	var bone_names := [
		"Sp_Hi_Tail0_B_00", "Sp_Hi_Tail0_B_01", "Sp_Hi_Tail0_B_02",
		"Sp_Hi_Tail0_B_03", "Sp_Hi_Tail0_B_04",
	]
	const N := 5
	var bone_ids:  Array[int]        = []
	var base_rots: Array[Quaternion] = []
	var wag_axes:  Array[Vector3]    = []
	var world_wag := Vector3(0.0, 0.0, 1.0)

	for bname in bone_names:
		var bid := sk.find_bone(bname)
		bone_ids.append(bid)
		if bid < 0:
			base_rots.append(Quaternion.IDENTITY)
			wag_axes.append(world_wag)
			continue
		base_rots.append(sk.get_bone_rest(bid).basis.get_rotation_quaternion())
		var gr := sk.get_bone_global_rest(bid)
		wag_axes.append((gr.basis.inverse() * world_wag).normalized())

	# ── 时间常量 ────────────────────────────────────────────────────
	const T_LIFT  := 0.22   # 上抬段时长（秒）
	const T_FALL  := 0.50   # 下落段时长（秒）
	# T_WAG = 0.72，T_END = T_WAG + PHASE_DLY[4] = 0.92（末骨落定）
	const T_END   := 0.92
	const MAX_AMP := 28.0   # 基础最大摆角（度）
	# 骨链传导延迟：根骨先动，末骨依次跟随
	var PHASE_DLY := [0.0, 0.045, 0.09, 0.14, 0.20]

	# ── 耳朵基准（自然微颤）────────────────────────────────────────────
	var ear_bone_names := ["Ear_01_L", "Ear_01_R", "Ear_02_L", "Ear_02_R", "Ear_03_L", "Ear_03_R"]
	var ear_ids:   Array[int]        = []
	var ear_rots:  Array[Quaternion] = []
	var ear_axes:  Array[Vector3]    = []
	var world_ear := Vector3(1.0, 0.0, 0.0)  # 调轴：X=前后倾，Z=左右扇
	for bname in ear_bone_names:
		var bid := sk.find_bone(bname)
		ear_ids.append(bid)
		if bid < 0:
			ear_rots.append(Quaternion.IDENTITY)
			ear_axes.append(world_ear)
			continue
		ear_rots.append(sk.get_bone_rest(bid).basis.get_rotation_quaternion())
		var gr := sk.get_bone_global_rest(bid)
		ear_axes.append((gr.basis.inverse() * world_ear).normalized())
	const EAR_AMPS  := [3.0,  3.0,  1.5,  1.5,  0.8,  0.8]  # 幅度（度）：根/根/中/中/尖/尖
	const EAR_FREQS := [0.37, 0.41, 0.53, 0.57, 0.61, 0.65]  # Hz
	const EAR_PHASE := [0.0,  1.1,  0.6,  1.7,  1.2,  2.3]   # 相位偏移（弧度）

	# ── 状态 / 模式 ID ──────────────────────────────────────────────
	const ST_IDLE      := 0
	const ST_WAG       := 1
	const ST_PAUSE_MID := 2   # DELAYED_PAIR 两摆之间的静止停顿

	const MD_SINGLE       := 0
	const MD_ALTERNATE    := 1
	const MD_DELAYED_PAIR := 2

	var rng := RandomNumberGenerator.new()
	rng.randomize()

	# ── 共享状态字典（闭包捕获） ─────────────────────────────────────
	var S := {
		"state":       ST_IDLE,
		"t":           0.0,
		"idle_dur":    rng.randf_range(1.5, 3.0),  # 首次等待略短
		"dir":         1.0,
		"last_dir":    -1.0,         # 让第一次摆向右（+Z）
		"mode":        MD_SINGLE,
		"alt_left":    0,            # ALTERNATE 还剩几次换向
		"pause_dur":   0.0,
		"pending_dir": 1.0,          # DELAYED_PAIR 第二摆方向
		"amp":         MAX_AMP,      # 当次摆幅（含随机抖动）
		"prev_ms":     -1.0,
	}

	# ── 单骨角度（含相位延迟） ────────────────────────────────────────
	var _bone_angle := func(i: int, tw: float, amp: float) -> float:
		var lt: float = tw - PHASE_DLY[i]
		if lt <= 0.0:
			return 0.0
		if lt <= T_LIFT:
			# 上抬：sin 曲线，快起慢收
			return amp * sin(lt / T_LIFT * PI * 0.5)
		var lf: float = lt - T_LIFT
		if lf <= T_FALL:
			# 下落：cos 曲线 —— 摆锤 SHM 精确解，顶慢底快，模拟重力感
			return amp * cos(lf / T_FALL * PI * 0.5)
		return 0.0

	# ── 发起新摆动（从 IDLE 进入） ────────────────────────────────────
	var _start_wag := func() -> void:
		S["dir"]      = -S["last_dir"]          # 方向与上次相反
		S["last_dir"] = S["dir"]
		S["amp"]      = MAX_AMP * rng.randf_range(0.85, 1.15)
		S["state"]    = ST_WAG
		S["t"]        = 0.0

		var roll: float = rng.randf()
		if roll < 0.50:
			S["mode"] = MD_SINGLE
		elif roll < 0.80:
			S["mode"]     = MD_ALTERNATE
			S["alt_left"] = rng.randi_range(1, 3)  # 额外换向次数
		else:
			S["mode"]        = MD_DELAYED_PAIR
			S["pending_dir"] = -S["dir"]

	# ── 每帧回调 ──────────────────────────────────────────────────────
	c.register_action_process(func() -> void:
		var now: float = Time.get_ticks_msec() * 0.001
		if S["prev_ms"] < 0.0:
			S["prev_ms"] = now
		S["t"]       += now - S["prev_ms"]
		S["prev_ms"]  = now

		if S["state"] == ST_IDLE:
			if S["t"] >= S["idle_dur"]:
				_start_wag.call()

		elif S["state"] == ST_WAG:
			var tw: float  = S["t"]
			var amp: float = S["dir"] * S["amp"]
			for i in range(N):
				if bone_ids[i] >= 0:
					sk.set_bone_pose_rotation(bone_ids[i],
						base_rots[i] * Quaternion(wag_axes[i],
							deg_to_rad(_bone_angle.call(i, tw, amp))))

			if tw >= T_END:
				# 归零
				for i in range(N):
					if bone_ids[i] >= 0:
						sk.set_bone_pose_rotation(bone_ids[i], base_rots[i])
				# 决定后续行为
				if S["mode"] == MD_SINGLE:
					S["state"]    = ST_IDLE
					S["t"]        = 0.0
					S["idle_dur"] = rng.randf_range(2.5, 5.0)

				elif S["mode"] == MD_ALTERNATE:
					if S["alt_left"] > 0:
						S["alt_left"] -= 1
						S["dir"]       = -S["dir"]
						S["last_dir"]  = S["dir"]
						S["amp"]       = MAX_AMP * rng.randf_range(0.85, 1.15)
						S["t"]         = 0.0
						# state 保持 ST_WAG，方向已翻转
					else:
						S["state"]    = ST_IDLE
						S["t"]        = 0.0
						S["idle_dur"] = rng.randf_range(3.0, 6.0)

				elif S["mode"] == MD_DELAYED_PAIR:
					# 第一摆结束 → 进入停顿，准备第二摆
					S["state"]     = ST_PAUSE_MID
					S["t"]         = 0.0
					S["pause_dur"] = rng.randf_range(2.0, 5.0)
					S["dir"]       = S["pending_dir"]
					S["last_dir"]  = S["dir"]
					S["mode"]      = MD_SINGLE  # 第二摆结束后回 IDLE

		elif S["state"] == ST_PAUSE_MID:
			if S["t"] >= S["pause_dur"]:
				S["amp"]   = MAX_AMP * rng.randf_range(0.85, 1.15)
				S["state"] = ST_WAG
				S["t"]     = 0.0

		# 耳朵微颤（每帧，独立于尾巴状态机）
		for ei in range(ear_ids.size()):
			if ear_ids[ei] >= 0:
				sk.set_bone_pose_rotation(ear_ids[ei],
					ear_rots[ei] * Quaternion(ear_axes[ei],
						deg_to_rad(EAR_AMPS[ei] * sin(now * EAR_FREQS[ei] * TAU + EAR_PHASE[ei]))))
	)

	# ── 清场 ──────────────────────────────────────────────────────────
	c.register_action_cleanup(func() -> void:
		for i in range(N):
			if bone_ids[i] >= 0:
				sk.set_bone_pose_rotation(bone_ids[i], base_rots[i])
		for ei in range(ear_ids.size()):
			if ear_ids[ei] >= 0:
				sk.set_bone_pose_rotation(ear_ids[ei], ear_rots[ei])
	)

	var tween := c.create_tween()
	tween.tween_interval(3600.0)
	return tween

# action_cheer.gd — 加油打气动作：尾巴高频欢快摇动 + 双手握拳加油
#
# 备份自 action_excited.gd
#
# 尾巴：比 happy 频率更高、幅度略大的正弦摆动
#
# 手臂（T_ARM_IN 秒渐入后持续上下泵动）：
#   Arm_L:   X=-15°  Z=-15°(略向前)
#   Arm_R:   X=-15°  Z=+15°
#   Elbow_L: Z=-120°(小臂高举成加油姿)  ±PUMP_AMP 上下泵动
#   Elbow_R: Z=+120°                   ±PUMP_AMP 上下泵动（与左臂反相，形成交替打气）

func play(c: Node3D, on_finish: Callable) -> Tween:
	var sk: Skeleton3D = c._skeleton
	if sk == null:
		var t := c.create_tween()
		t.tween_interval(0.01)
		t.finished.connect(on_finish, CONNECT_ONE_SHOT)
		return t

	# ── 尾巴骨骼 ─────────────────────────────────────────────────────────────
	var bone_names := [
		"Sp_Hi_Tail0_B_00",
		"Sp_Hi_Tail0_B_01",
		"Sp_Hi_Tail0_B_02",
		"Sp_Hi_Tail0_B_03",
		"Sp_Hi_Tail0_B_04",
	]
	var bone_ids:   Array[int]        = []
	var base_rots:  Array[Quaternion] = []
	var wag_axes:   Array[Vector3]    = []
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

	const FREQ       := 1.7
	const PHASE_STEP := 0.2
	const AMPLITUDES := [12.0, 18.0, 26.0, 33.0, 40.0]

	# ── 耳朵骨骼 ─────────────────────────────────────────────────────────────
	var ear_bone_names := ["Ear_01_L", "Ear_01_R", "Ear_02_L", "Ear_02_R", "Ear_03_L", "Ear_03_R"]
	var ear_ids:   Array[int]        = []
	var ear_rots:  Array[Quaternion] = []
	var ear_axes:  Array[Vector3]    = []
	var world_ear := Vector3(1.0, 0.0, 0.0)
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
	const EAR_AMPS  := [3.0,  3.0,  1.5,  1.5,  0.8,  0.8]
	const EAR_FREQS := [0.37, 0.41, 0.53, 0.57, 0.61, 0.65]
	const EAR_PHASE := [0.0,  1.1,  0.6,  1.7,  1.2,  2.3]

	# ── 手臂骨骼（握拳加油，交替上下泵动）───────────────────────────────────
	var arm_bone_names := ["Arm_L", "Arm_R", "Elbow_L", "Elbow_R"]
	var arm_ids:  Array[int]        = []
	var arm_prev: Array[Quaternion] = []

	for bname in arm_bone_names:
		var bid := sk.find_bone(bname)
		arm_ids.append(bid)
		arm_prev.append(sk.get_bone_pose_rotation(bid) if bid >= 0 else Quaternion.IDENTITY)

	var arm_targets: Array[Quaternion] = [
		Quaternion(Vector3(0,0,1), deg_to_rad(-15.0)) * Quaternion(Vector3(1,0,0), deg_to_rad(-15.0)),  # Arm_L
		Quaternion(Vector3(0,0,1), deg_to_rad( 15.0)) * Quaternion(Vector3(1,0,0), deg_to_rad(-15.0)),  # Arm_R
		Quaternion(Vector3(0,0,1), deg_to_rad(-120.0)),  # Elbow_L
		Quaternion(Vector3(0,0,1), deg_to_rad( 120.0)),  # Elbow_R
	]
	const T_ARM_IN  := 0.35
	const PUMP_AMP  := 12.0
	const PUMP_FREQ := 2.2

	var start_time := Time.get_ticks_msec() * 0.001

	c.register_action_process(func() -> void:
		var t       := Time.get_ticks_msec() * 0.001
		var elapsed := t - start_time
		var arm_blend := minf(elapsed / T_ARM_IN, 1.0)

		# 尾巴摇摆
		for i in range(bone_ids.size()):
			if bone_ids[i] < 0:
				continue
			var phase: float = float(i) * PHASE_STEP
			var wag:   float = float(AMPLITUDES[i]) * sin(t * FREQ * TAU - phase * TAU)
			sk.set_bone_pose_rotation(bone_ids[i],
				base_rots[i] * Quaternion(wag_axes[i], deg_to_rad(wag)))

		# 耳朵微颤
		for ei in range(ear_ids.size()):
			if ear_ids[ei] >= 0:
				sk.set_bone_pose_rotation(ear_ids[ei],
					ear_rots[ei] * Quaternion(ear_axes[ei],
						deg_to_rad(EAR_AMPS[ei] * sin(t * EAR_FREQS[ei] * TAU + EAR_PHASE[ei]))))

		# 手臂基础渐入
		sk.set_bone_pose_rotation(arm_ids[0], arm_prev[0].slerp(arm_targets[0], arm_blend)) if arm_ids[0] >= 0 else null
		sk.set_bone_pose_rotation(arm_ids[1], arm_prev[1].slerp(arm_targets[1], arm_blend)) if arm_ids[1] >= 0 else null

		# 肘部加油泵动（渐入完成后）：左右反相，形成交替打气感
		var pump: float = sin(t * PUMP_FREQ * TAU) * PUMP_AMP * arm_blend
		if arm_ids[2] >= 0:
			sk.set_bone_pose_rotation(arm_ids[2],
				arm_prev[2].slerp(arm_targets[2], arm_blend)
				* Quaternion(Vector3(0,0,1), deg_to_rad(pump)))
		if arm_ids[3] >= 0:
			sk.set_bone_pose_rotation(arm_ids[3],
				arm_prev[3].slerp(arm_targets[3], arm_blend)
				* Quaternion(Vector3(0,0,1), deg_to_rad(-pump)))
	)

	c.register_action_cleanup(func() -> void:
		for ai in range(arm_ids.size()):
			if arm_ids[ai] >= 0:
				sk.set_bone_pose_rotation(arm_ids[ai], arm_prev[ai])
		for i in range(bone_ids.size()):
			if bone_ids[i] >= 0:
				sk.set_bone_pose_rotation(bone_ids[i], base_rots[i])
		for ei in range(ear_ids.size()):
			if ear_ids[ei] >= 0:
				sk.set_bone_pose_rotation(ear_ids[ei], ear_rots[ei])
	)

	var tween := c.create_tween()
	tween.tween_interval(3600.0)
	return tween

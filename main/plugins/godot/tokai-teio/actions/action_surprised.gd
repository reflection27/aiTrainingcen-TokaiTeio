# action_surprised.gd — 惊讶动作：耳朵竖立 + 双手举至下巴 + 尾巴突然上竖后落下
#
# 时间线（耳朵）：
#   [0,       T_RISE]           : 快速竖立
#   [T_RISE,  T_RISE+T_HOLD]    : 顶点短暂保持
#   [T_HOLD+, T_HOLD+T_DECAY]   : 缓慢恢复
#   之后                        : 基准微颤
#
# 时间线（手臂，双手举至下巴前掌心朝口）：
#   [0,       T_ARM_UP]         : 双手快速上抬
#   [T_ARM_UP, T_ARM_UP+T_HOLD_ARMS] : 保持举起
#   [T_ARM_UP+T_HOLD_ARMS, ...]  : 缓慢放下
#
#   Arm_L:   X=-15°(略下)  Z=-15°(略向前)
#   Arm_R:   X=-15°        Z=+15°
#   Elbow_L: Z=-110°(小臂上抬至下巴前)
#   Elbow_R: Z=+110°
#   Wrist_L: Z=+20°(掌心朝内朝口)   Wrist_R: Z=-20°
#
# 时间线（尾巴）：
#   [0,       T_TAIL_SPIKE]     : 突然上竖（快速 ease-out）
#   [T_TAIL_SPIKE, T_TAIL_SPIKE+T_TAIL_HOLD] : 保持竖立
#   [T_TAIL_SPIKE+T_TAIL_HOLD, ...] : 随重力落下（ease-in，二次加速）

func play(c: Node3D, on_finish: Callable) -> Tween:
	var sk: Skeleton3D = c._skeleton
	if sk == null:
		var tw := c.create_tween()
		tw.tween_interval(0.01)
		tw.finished.connect(on_finish, CONNECT_ONE_SHOT)
		return tw

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

	const PERK_ANGS := [-18.0, -18.0, -10.0, -10.0, -5.0, -5.0]
	const T_RISE  := 0.12
	const T_HOLD  := 0.20
	const T_DECAY := 1.80
	const EAR_AMPS  := [3.0,  3.0,  1.5,  1.5,  0.8,  0.8]
	const EAR_FREQS := [0.37, 0.41, 0.53, 0.57, 0.61, 0.65]
	const EAR_PHASE := [0.0,  1.1,  0.6,  1.7,  1.2,  2.3]

	# ── 尾巴骨骼 ─────────────────────────────────────────────────────────────
	var tail_bone_names := [
		"Sp_Hi_Tail0_B_00", "Sp_Hi_Tail0_B_01", "Sp_Hi_Tail0_B_02",
		"Sp_Hi_Tail0_B_03", "Sp_Hi_Tail0_B_04",
	]
	var tail_ids:  Array[int]        = []
	var tail_rots: Array[Quaternion] = []
	var tail_axes: Array[Vector3]    = []
	var world_tail := Vector3(1.0, 0.0, 0.0)  # 世界 X 轴：正 = 斜向后上方，负 = 向前下方

	for bname in tail_bone_names:
		var bid := sk.find_bone(bname)
		tail_ids.append(bid)
		if bid < 0:
			tail_rots.append(Quaternion.IDENTITY)
			tail_axes.append(world_tail)
			continue
		tail_rots.append(sk.get_bone_rest(bid).basis.get_rotation_quaternion())
		var gr := sk.get_bone_global_rest(bid)
		tail_axes.append((gr.basis.inverse() * world_tail).normalized())

	# 根骨大幅上抬，后续骨节逐渐归零 = 尾巴根部竖起、末端自然伸直
	const TAIL_SPIKE_AMPS := [95.0, 18.3, 0.0, 0.0, 0.0]
	const T_TAIL_SPIKE    := 0.10   # 突然上竖时长（秒）
	const T_TAIL_HOLD     := 0.15   # 竖立保持
	const T_TAIL_FALL     := 1.20   # 随重力落下时长

	# ── 手臂骨骼 ─────────────────────────────────────────────────────────────
	var arm_bone_names := ["Arm_L", "Arm_R", "Elbow_L", "Elbow_R", "Wrist_L", "Wrist_R"]
	var arm_ids:  Array[int]        = []
	var arm_prev: Array[Quaternion] = []

	for bname in arm_bone_names:
		var bid := sk.find_bone(bname)
		arm_ids.append(bid)
		arm_prev.append(sk.get_bone_pose_rotation(bid) if bid >= 0 else Quaternion.IDENTITY)

	# 举起目标姿态（掌心朝口，值可在 Godot 内调参）
	var arm_targets: Array[Quaternion] = [
		Quaternion(Vector3(0,0,1), deg_to_rad(-15.0)) * Quaternion(Vector3(1,0,0), deg_to_rad(-15.0)),  # Arm_L
		Quaternion(Vector3(0,0,1), deg_to_rad( 15.0)) * Quaternion(Vector3(1,0,0), deg_to_rad(-15.0)),  # Arm_R
		Quaternion(Vector3(0,0,1), deg_to_rad(-110.0)),  # Elbow_L
		Quaternion(Vector3(0,0,1), deg_to_rad( 110.0)),  # Elbow_R
		Quaternion(Vector3(0,1,0), deg_to_rad(-135.0)),   # Wrist_L（掌心朝内）
		Quaternion(Vector3(0,1,0), deg_to_rad( 135.0)),   # Wrist_R（掌心朝内）
	]

	const T_ARM_UP        := 0.20   # 双手上抬时长
	const T_HOLD_ARMS     := 2.50   # 举起保持时长
	const T_ARM_DOWN      := 0.60   # 缓慢放下时长

	var start_time := Time.get_ticks_msec() * 0.001

	c.register_action_process(func() -> void:
		var t:       float = Time.get_ticks_msec() * 0.001
		var elapsed: float = t - start_time

		# ── 耳朵竖立 ────────────────────────────────────────────────────────
		var perk: float
		if elapsed < T_RISE:
			perk = elapsed / T_RISE
		elif elapsed < T_RISE + T_HOLD:
			perk = 1.0
		else:
			var d: float = (elapsed - T_RISE - T_HOLD) / T_DECAY
			perk = maxf(1.0 - d * d, 0.0)

		for ei in range(ear_ids.size()):
			if ear_ids[ei] >= 0:
				var tremble: float = EAR_AMPS[ei] * sin(t * EAR_FREQS[ei] * TAU + EAR_PHASE[ei]) * (1.0 - perk)
				var ang: float     = PERK_ANGS[ei] * perk + tremble
				sk.set_bone_pose_rotation(ear_ids[ei],
					ear_rots[ei] * Quaternion(ear_axes[ei], deg_to_rad(ang)))

		# ── 尾巴突然上竖后随重力落下 ─────────────────────────────────────────
		var tail_blend: float
		if elapsed < T_TAIL_SPIKE:
			# ease-out：快速上竖
			var d := elapsed / T_TAIL_SPIKE
			tail_blend = 1.0 - (1.0 - d) * (1.0 - d)
		elif elapsed < T_TAIL_SPIKE + T_TAIL_HOLD:
			tail_blend = 1.0
		else:
			# ease-in：随重力加速落下，二次曲线
			var d := minf((elapsed - T_TAIL_SPIKE - T_TAIL_HOLD) / T_TAIL_FALL, 1.0)
			tail_blend = maxf(1.0 - d * d, 0.0)

		for ti in range(tail_ids.size()):
			if tail_ids[ti] >= 0:
				sk.set_bone_pose_rotation(tail_ids[ti],
					tail_rots[ti] * Quaternion(tail_axes[ti], deg_to_rad(TAIL_SPIKE_AMPS[ti] * tail_blend)))

		# ── 双手举至下巴前（有时间限制，之后放下）──────────────────────────
		var arm_blend: float
		if elapsed < T_ARM_UP:
			arm_blend = elapsed / T_ARM_UP
		elif elapsed < T_ARM_UP + T_HOLD_ARMS:
			arm_blend = 1.0
		else:
			var d := minf((elapsed - T_ARM_UP - T_HOLD_ARMS) / T_ARM_DOWN, 1.0)
			arm_blend = 1.0 - d

		for ai in range(arm_ids.size()):
			if arm_ids[ai] >= 0:
				sk.set_bone_pose_rotation(arm_ids[ai],
					arm_prev[ai].slerp(arm_targets[ai], arm_blend))
	)

	c.register_action_cleanup(func() -> void:
		for ai in range(arm_ids.size()):
			if arm_ids[ai] >= 0:
				sk.set_bone_pose_rotation(arm_ids[ai], arm_prev[ai])
		for ti in range(tail_ids.size()):
			if tail_ids[ti] >= 0:
				sk.set_bone_pose_rotation(tail_ids[ti], tail_rots[ti])
		for ei in range(ear_ids.size()):
			if ear_ids[ei] >= 0:
				sk.set_bone_pose_rotation(ear_ids[ei], ear_rots[ei])
	)

	var tween := c.create_tween()
	tween.tween_interval(3600.0)
	return tween

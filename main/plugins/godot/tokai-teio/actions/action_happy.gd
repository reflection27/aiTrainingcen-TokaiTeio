# action_happy.gd — 开心动作：尾巴欢快摇动（峰顶停留等末骨）+ 双手背到身后
#
# 尾巴波形（自定义，1 PERIOD 内六段）：
#   [0,       T_SWING ]  : 0 → +1  (sin，快速上摆)
#   [T_SWING, T_SWING+T_HOLD] : hold +1 (顶点停留，等末骨到达)
#   [+,       +T_SWING]  : +1 → 0  (cos，快速下落)
#   [+,       +T_SWING]  : 0 → -1  (sin，快速下摆)
#   [+,       +T_HOLD ]  : hold -1
#   [+,       +T_SWING]  : -1 → 0  (cos，快速回归)
#
# 双手背到身后收拢（T_ARM_IN 秒渐入，保持不动）：
#   Arm_L:   Z=+50°(向后)  Y=-15°(内旋收拢)  X=-30°(略下)
#   Arm_R:   Z=-50°        Y=+15°             X=-30°
#   Elbow_L: Z=+70°(小臂向后收，与挥手符号相反)
#   Elbow_R: Z=-70°

func play(c: Node3D, on_finish: Callable) -> Tween:
	var sk: Skeleton3D = c._skeleton
	if sk == null:
		var t := c.create_tween()
		t.tween_interval(0.01)
		t.finished.connect(on_finish, CONNECT_ONE_SHOT)
		return t

	# ── 尾巴骨骼 ─────────────────────────────────────────────────────────────
	var bone_names := [
		"Sp_Hi_Tail0_B_00", "Sp_Hi_Tail0_B_01", "Sp_Hi_Tail0_B_02",
		"Sp_Hi_Tail0_B_03", "Sp_Hi_Tail0_B_04",
	]
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

	const PERIOD   := 2.0
	const T_SWING  := 0.425
	const T_HOLD   := 0.15
	const BONE_DLY := 0.035
	const AMPLITUDES := [20.0, 28.0, 38.0, 48.0, 58.0]

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

	# ── 手臂骨骼（背手）──────────────────────────────────────────────────────
	var arm_bone_names := ["Arm_L", "Arm_R", "Elbow_L", "Elbow_R"]
	var arm_ids:  Array[int]        = []
	var arm_prev: Array[Quaternion] = []  # 进入前的姿态，cleanup 时恢复

	for bname in arm_bone_names:
		var bid := sk.find_bone(bname)
		arm_ids.append(bid)
		arm_prev.append(sk.get_bone_pose_rotation(bid) if bid >= 0 else Quaternion.IDENTITY)

	# 背手目标姿态（值可在 Godot 内调参）
	# Arm Z+/Z- 控制前后；Elbow 符号与挥手相反才能让小臂往身后收
	# Y 轴内旋让双手在背后靠拢，X 略下保证自然垂感
	var arm_targets: Array[Quaternion] = [
		Quaternion(Vector3(0,0,1), deg_to_rad( 50.0)) * Quaternion(Vector3(0,1,0), deg_to_rad(-15.0)) * Quaternion(Vector3(1,0,0), deg_to_rad(-30.0)),  # Arm_L
		Quaternion(Vector3(0,0,1), deg_to_rad(-50.0)) * Quaternion(Vector3(0,1,0), deg_to_rad( 15.0)) * Quaternion(Vector3(1,0,0), deg_to_rad(-30.0)),  # Arm_R
		Quaternion(Vector3(0,0,1), deg_to_rad( 70.0)),  # Elbow_L（正号朝后，与挥手反向）
		Quaternion(Vector3(0,0,1), deg_to_rad(-70.0)),  # Elbow_R
	]
	const T_ARM_IN := 0.5  # 手臂渐入时长（秒）

	# ── 尾巴波形节点时间 ──────────────────────────────────────────────────────
	const TP1 := T_SWING
	const TP2 := T_SWING + T_HOLD
	const TP3 := T_SWING * 2.0 + T_HOLD
	const TP4 := T_SWING * 3.0 + T_HOLD
	const TP5 := T_SWING * 3.0 + T_HOLD * 2.0

	var _wave := func(tp: float) -> float:
		if tp < TP1:
			return sin(tp / T_SWING * PI * 0.5)
		elif tp < TP2:
			return 1.0
		elif tp < TP3:
			return cos((tp - TP2) / T_SWING * PI * 0.5)
		elif tp < TP4:
			return -sin((tp - TP3) / T_SWING * PI * 0.5)
		elif tp < TP5:
			return -1.0
		else:
			return -cos((tp - TP5) / T_SWING * PI * 0.5)

	var start_time := Time.get_ticks_msec() * 0.001

	c.register_action_process(func() -> void:
		var now     := Time.get_ticks_msec() * 0.001
		var elapsed := now - start_time

		# 手臂背后（渐入）
		var arm_blend := minf(elapsed / T_ARM_IN, 1.0)
		for ai in range(arm_ids.size()):
			if arm_ids[ai] >= 0:
				sk.set_bone_pose_rotation(arm_ids[ai],
					arm_prev[ai].slerp(arm_targets[ai], arm_blend))

		# 尾巴摇摆
		for i in range(bone_ids.size()):
			if bone_ids[i] < 0:
				continue
			var tp: float = fmod(now - float(i) * BONE_DLY, PERIOD)
			if tp < 0.0:
				tp += PERIOD
			var wag: float = _wave.call(tp) * AMPLITUDES[i]
			sk.set_bone_pose_rotation(bone_ids[i],
				base_rots[i] * Quaternion(wag_axes[i], deg_to_rad(wag)))

		# 耳朵微颤
		for ei in range(ear_ids.size()):
			if ear_ids[ei] >= 0:
				sk.set_bone_pose_rotation(ear_ids[ei],
					ear_rots[ei] * Quaternion(ear_axes[ei],
						deg_to_rad(EAR_AMPS[ei] * sin(now * EAR_FREQS[ei] * TAU + EAR_PHASE[ei]))))
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

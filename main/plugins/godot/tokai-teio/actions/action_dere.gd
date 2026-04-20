# action_dere.gd — 害羞/腹黑动作：耳朵自然微颤 + 双手放肚子前食指对戳
#
# 手臂（T_ARM_IN 秒渐入，保持不动）：
#   Arm_L:   X=-20°(略下)  Z=-20°(向前)  Y=+15°(向内靠拢)
#   Arm_R:   X=-20°        Z=+20°        Y=-15°
#   Elbow_L: Z=-55°(小臂弯折至肚子前)
#   Elbow_R: Z=+55°
# 两食指向中心靠拢，呈"戳戳"状

func play(c: Node3D, on_finish: Callable) -> Tween:
	var sk: Skeleton3D = c._skeleton
	if sk == null:
		var tw := c.create_tween()
		tw.tween_interval(0.01)
		tw.finished.connect(on_finish, CONNECT_ONE_SHOT)
		return tw

	# ── 耳朵骨骼（自然微颤）──────────────────────────────────────────────────
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

	# ── 手臂骨骼（食指对戳）──────────────────────────────────────────────────
	var arm_bone_names := ["Arm_L", "Arm_R", "Elbow_L", "Elbow_R", "Wrist_L", "Wrist_R"]
	var arm_ids:  Array[int]        = []
	var arm_prev: Array[Quaternion] = []

	for bname in arm_bone_names:
		var bid := sk.find_bone(bname)
		arm_ids.append(bid)
		arm_prev.append(sk.get_bone_pose_rotation(bid) if bid >= 0 else Quaternion.IDENTITY)

	# 食指对戳目标姿态（值可在 Godot 内调参）
	var arm_targets: Array[Quaternion] = [
		Quaternion(Vector3(1,0,0), deg_to_rad(-55.0)) * Quaternion(Vector3(0,1,0), deg_to_rad( 90.0)) * Quaternion(Vector3(0,0,1), deg_to_rad( 20.0)),  # Arm_L
		Quaternion(Vector3(1,0,0), deg_to_rad(-55.0)) * Quaternion(Vector3(0,1,0), deg_to_rad(-90.0)) * Quaternion(Vector3(0,0,1), deg_to_rad(-20.0)),  # Arm_R
		Quaternion(Vector3(0,0,1), deg_to_rad(-60.0)) * Quaternion(Vector3(1,0,0), deg_to_rad( 30.0)),  # Elbow_L
		Quaternion(Vector3(0,0,1), deg_to_rad( 60.0)) * Quaternion(Vector3(1,0,0), deg_to_rad( 30.0)),  # Elbow_R
		Quaternion(Vector3(0,1,0), deg_to_rad( -50.0)) * Quaternion(Vector3(1,0,0), deg_to_rad(-75.0)) * Quaternion(Vector3(0,0,1), deg_to_rad( 0.0)),  # Wrist_L
		Quaternion(Vector3(0,1,0), deg_to_rad( 50.0)) * Quaternion(Vector3(1,0,0), deg_to_rad(-75.0)) * Quaternion(Vector3(0,0,1), deg_to_rad( 0.0)),  # Wrist_R
	]
	const T_ARM_IN := 0.5

	# 食指轻微戳动动画参数（小幅来回）
	const POKE_AMP  := 5.0   # 戳动幅度（度）
	const POKE_FREQ := 1.2   # 戳动频率（Hz）

	# ── 手指骨骼 ──────────────────────────────────────────────────────────────
	# 食指伸直（不控制），拇指略微下压，中/无名/小拇指握拳
	var finger_bone_names := [
		"Thumb_01_L",  "Thumb_02_L",  "Thumb_03_L",
		"Middle_01_L", "Middle_02_L", "Middle_03_L",
		"Ring_01_L",   "Ring_02_L",   "Ring_03_L",
		"Pinky_01_L",  "Pinky_02_L",  "Pinky_03_L",
		"Thumb_01_R",  "Thumb_02_R",  "Thumb_03_R",
		"Middle_01_R", "Middle_02_R", "Middle_03_R",
		"Ring_01_R",   "Ring_02_R",   "Ring_03_R",
		"Pinky_01_R",  "Pinky_02_R",  "Pinky_03_R",
	]
	var finger_ids:  Array[int]        = []
	var finger_prev: Array[Quaternion] = []
	for bname in finger_bone_names:
		var bid := sk.find_bone(bname)
		finger_ids.append(bid)
		finger_prev.append(sk.get_bone_pose_rotation(bid) if bid >= 0 else Quaternion.IDENTITY)

	const THUMB_PRESS := 15.0  # 拇指下压幅度
	const FIST_ANG    := 80.0  # 握拳弯曲角度

	var finger_targets: Array[Quaternion] = [
		Quaternion(Vector3(1,0,0), deg_to_rad(-THUMB_PRESS)),  # Thumb_01_L
		Quaternion(Vector3(1,0,0), deg_to_rad(-THUMB_PRESS)),  # Thumb_02_L
		Quaternion(Vector3(1,0,0), deg_to_rad(-THUMB_PRESS)),  # Thumb_03_L
		Quaternion(Vector3(1,0,0), deg_to_rad(-FIST_ANG)),     # Middle_01_L
		Quaternion(Vector3(1,0,0), deg_to_rad(-FIST_ANG)),     # Middle_02_L
		Quaternion(Vector3(1,0,0), deg_to_rad(-FIST_ANG)),     # Middle_03_L
		Quaternion(Vector3(1,0,0), deg_to_rad(-FIST_ANG)),     # Ring_01_L
		Quaternion(Vector3(1,0,0), deg_to_rad(-FIST_ANG)),     # Ring_02_L
		Quaternion(Vector3(1,0,0), deg_to_rad(-FIST_ANG)),     # Ring_03_L
		Quaternion(Vector3(1,0,0), deg_to_rad(-FIST_ANG)),     # Pinky_01_L
		Quaternion(Vector3(1,0,0), deg_to_rad(-FIST_ANG)),     # Pinky_02_L
		Quaternion(Vector3(1,0,0), deg_to_rad(-FIST_ANG)),     # Pinky_03_L
		Quaternion(Vector3(1,0,0), deg_to_rad(-THUMB_PRESS)),  # Thumb_01_R
		Quaternion(Vector3(1,0,0), deg_to_rad(-THUMB_PRESS)),  # Thumb_02_R
		Quaternion(Vector3(1,0,0), deg_to_rad(-THUMB_PRESS)),  # Thumb_03_R
		Quaternion(Vector3(1,0,0), deg_to_rad(-FIST_ANG)),     # Middle_01_R
		Quaternion(Vector3(1,0,0), deg_to_rad(-FIST_ANG)),     # Middle_02_R
		Quaternion(Vector3(1,0,0), deg_to_rad(-FIST_ANG)),     # Middle_03_R
		Quaternion(Vector3(1,0,0), deg_to_rad(-FIST_ANG)),     # Ring_01_R
		Quaternion(Vector3(1,0,0), deg_to_rad(-FIST_ANG)),     # Ring_02_R
		Quaternion(Vector3(1,0,0), deg_to_rad(-FIST_ANG)),     # Ring_03_R
		Quaternion(Vector3(1,0,0), deg_to_rad(-FIST_ANG)),     # Pinky_01_R
		Quaternion(Vector3(1,0,0), deg_to_rad(-FIST_ANG)),     # Pinky_02_R
		Quaternion(Vector3(1,0,0), deg_to_rad(-FIST_ANG)),     # Pinky_03_R
	]

	var start_time := Time.get_ticks_msec() * 0.001

	c.register_action_process(func() -> void:
		var t       := Time.get_ticks_msec() * 0.001
		var elapsed := t - start_time
		var arm_blend := minf(elapsed / T_ARM_IN, 1.0)

		# 耳朵微颤
		for ei in range(ear_ids.size()):
			if ear_ids[ei] >= 0:
				sk.set_bone_pose_rotation(ear_ids[ei],
					ear_rots[ei] * Quaternion(ear_axes[ei],
						deg_to_rad(EAR_AMPS[ei] * sin(t * EAR_FREQS[ei] * TAU + EAR_PHASE[ei]))))

		# 手臂渐入基础姿态
		for ai in range(arm_ids.size()):
			if arm_ids[ai] >= 0:
				sk.set_bone_pose_rotation(arm_ids[ai],
					arm_prev[ai].slerp(arm_targets[ai], arm_blend))

		# 手指握姿渐入
		for fi in range(finger_ids.size()):
			if finger_ids[fi] >= 0:
				sk.set_bone_pose_rotation(finger_ids[fi],
					finger_prev[fi].slerp(finger_targets[fi], arm_blend))

		# 食指对戳：肘部小幅来回（戳动感），渐入后生效
		if arm_blend >= 1.0:
			var poke := deg_to_rad(POKE_AMP * sin(t * POKE_FREQ * TAU))
			if arm_ids[2] >= 0:  # Elbow_L（向中心靠拢）
				sk.set_bone_pose_rotation(arm_ids[2],
					arm_targets[2] * Quaternion(Vector3(0,0,1), -poke))
			if arm_ids[3] >= 0:  # Elbow_R（向中心靠拢）
				sk.set_bone_pose_rotation(arm_ids[3],
					arm_targets[3] * Quaternion(Vector3(0,0,1), poke))
	)

	c.register_action_cleanup(func() -> void:
		for ai in range(arm_ids.size()):
			if arm_ids[ai] >= 0:
				sk.set_bone_pose_rotation(arm_ids[ai], arm_prev[ai])
		for fi in range(finger_ids.size()):
			if finger_ids[fi] >= 0:
				sk.set_bone_pose_rotation(finger_ids[fi], finger_prev[fi])
		for ei in range(ear_ids.size()):
			if ear_ids[ei] >= 0:
				sk.set_bone_pose_rotation(ear_ids[ei], ear_rots[ei])
	)

	var tween := c.create_tween()
	tween.tween_interval(3600.0)
	return tween

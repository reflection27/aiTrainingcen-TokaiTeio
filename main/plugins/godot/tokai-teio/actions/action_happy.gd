# action_happy.gd  —— 开心动作：尾巴欢快摇动
#
# 进入动作时先 reset 各尾骨（= normal 状态基准），捕获 rest 旋转，
# 然后在此基础上叠加左右摇摆。

func play(c: Node3D, on_finish: Callable) -> Tween:
	var sk: Skeleton3D = c._skeleton
	if sk == null:
		var t := c.create_tween()
		t.tween_interval(0.01)
		t.finished.connect(on_finish, CONNECT_ONE_SHOT)
		return t

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

	var world_wag := Vector3(0.0, 0.0, 1.0)  # 世界左右轴

	for bname in bone_names:
		var bid := sk.find_bone(bname)
		bone_ids.append(bid)
		if bid < 0:
			base_rots.append(Quaternion.IDENTITY)
			wag_axes.append(world_wag)
			continue
		# 只取 rest 旋转分量，不 reset（避免 reset_bone_pose 把 scale 也还原成展开状态）
		base_rots.append(sk.get_bone_rest(bid).basis.get_rotation_quaternion())
		# 将世界左右轴转换到骨骼局部空间
		var gr := sk.get_bone_global_rest(bid)
		wag_axes.append((gr.basis.inverse() * world_wag).normalized())

	const FREQ       := 2.0
	const PHASE_STEP := 0.2
	const AMPLITUDES := [10.0, 15.0, 22.0, 28.0, 34.0]

	c.register_action_process(func() -> void:
		var t := Time.get_ticks_msec() * 0.001
		for i in range(bone_ids.size()):
			if bone_ids[i] < 0:
				continue
			var phase: float = float(i) * PHASE_STEP
			var wag:   float = float(AMPLITUDES[i]) * sin(t * FREQ * TAU + phase * TAU)
			# 叠加在 normal 基准旋转上
			sk.set_bone_pose_rotation(bone_ids[i],
				base_rots[i] * Quaternion(wag_axes[i], deg_to_rad(wag)))
	)

	c.register_action_cleanup(func() -> void:
		for i in range(bone_ids.size()):
			if bone_ids[i] >= 0:
				# 只还原旋转，不碰 scale/position
				sk.set_bone_pose_rotation(bone_ids[i], base_rots[i])
	)

	var tween := c.create_tween()
	tween.tween_interval(3600.0)
	return tween

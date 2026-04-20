# action_sad.gd — 悲伤动作：耳朵向前耷拉（下垂）
#
# 耳朵行为：
#   0.5s 缓慢向前垂下（ease-out，沉重感）→ 静止保持（无颤抖，静 = 悲）
#
# 调参说明：
#   DROOP_ANGS  负值 = 向前垂；若方向反了改为正值
#   Ear_01 绝对值 > Ear_02 → 根部前倾更多，耳尖向下耷拉

func play(c: Node3D, on_finish: Callable) -> Tween:
	var sk: Skeleton3D = c._skeleton
	if sk == null:
		var tw := c.create_tween()
		tw.tween_interval(0.01)
		tw.finished.connect(on_finish, CONNECT_ONE_SHOT)
		return tw

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

	const DROOP_ANGS := [25.0, 25.0, 15.0, 15.0, 8.0, 8.0]  # 目标角度（度）：L根/R根/L中/R中/L尖/R尖
	const T_DROOP    := 0.5                             # 垂下时长（秒）

	var start_time := Time.get_ticks_msec() * 0.001

	c.register_action_process(func() -> void:
		var t: float     = Time.get_ticks_msec() * 0.001
		var lin: float   = minf((t - start_time) / T_DROOP, 1.0)
		var blend: float = 1.0 - pow(1.0 - lin, 2.0)  # ease-out 二次，快起慢停
		for ei in range(ear_ids.size()):
			if ear_ids[ei] >= 0:
				var ang: float = DROOP_ANGS[ei] * blend
				sk.set_bone_pose_rotation(ear_ids[ei],
					ear_rots[ei] * Quaternion(ear_axes[ei], deg_to_rad(ang)))
	)

	c.register_action_cleanup(func() -> void:
		for ei in range(ear_ids.size()):
			if ear_ids[ei] >= 0:
				sk.set_bone_pose_rotation(ear_ids[ei], ear_rots[ei])
	)

	# TODO: 设计 sad 心情对应的肢体动作（尾巴/手臂等）
	var tween := c.create_tween()
	tween.tween_interval(3600.0)
	return tween

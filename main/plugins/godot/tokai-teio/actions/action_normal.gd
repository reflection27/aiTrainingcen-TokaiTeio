# action_normal.gd  —— 普通/待机动作
# 接口：static func play(c: Node3D, on_finish: Callable) -> Tween
#   c  : CharacterController 节点（可访问 c._skeleton、c.create_tween() 等）
#   on_finish : 动作结束后由主控传入的回调

func play(c: Node3D, on_finish: Callable) -> Tween:
	var tween := c.create_tween()
	# TODO: 设计 normal 心情对应的肢体动作
	tween.tween_interval(0.01)
	tween.finished.connect(on_finish, CONNECT_ONE_SHOT)
	return tween

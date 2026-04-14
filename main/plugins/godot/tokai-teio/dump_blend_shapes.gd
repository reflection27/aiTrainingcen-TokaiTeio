# dump_blend_shapes.gd
# 临时挂到 Main 节点，运行后在 Output 面板看所有 BlendShape 名字
# 用完删掉即可

extends Node

@onready var _character: Node3D = get_parent().get_node("CharacterRoot")

func _ready() -> void:
	await get_tree().process_frame
	await get_tree().process_frame  # 等模型加载完

	var all_shapes: Array[String] = []
	_collect(_character, all_shapes)
	all_shapes.sort()

	print("===== BlendShape 完整列表 (%d 个) =====" % all_shapes.size())
	for s in all_shapes:
		print(s)
	print("==========================================")

	# 单独过滤可能与眼睛高光相关的
	print("\n--- 眼睛相关 ---")
	for s in all_shapes:
		var l := s.to_lower()
		if "eye" in l or "hikari" in l or "hilight" in l or "highlight" in l or "pupil" in l:
			print(s)


func _collect(node: Node, out: Array[String]) -> void:
	if node is MeshInstance3D:
		var mi := node as MeshInstance3D
		if mi.mesh:
			for i in range(mi.mesh.get_blend_shape_count()):
				out.append(mi.mesh.get_blend_shape_name(i))
	for child in node.get_children():
		_collect(child, out)

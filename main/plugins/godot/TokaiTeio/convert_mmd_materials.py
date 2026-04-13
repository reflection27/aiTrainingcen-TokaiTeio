import bpy

for mat in bpy.data.materials:
    if not mat.use_nodes:
        continue
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    mmd_shader = nodes.get("mmd_shader")
    tex_node = nodes.get("mmd_base_tex")
    output_node = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)

    if not mmd_shader or not output_node:
        continue

    nodes.remove(mmd_shader)

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)

    if tex_node:
        links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])

    links.new(bsdf.outputs['BSDF'], output_node.inputs['Surface'])

print("转换完成")

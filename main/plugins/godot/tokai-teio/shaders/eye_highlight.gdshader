shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, unshaded;

uniform sampler2D texture_albedo : source_color, hint_default_white;

// 两眼共用 UV，V 方向上下各占一半，归一化到 0~1 后在同一位置打高光
// U 范围约 0.135~0.865，V 每只眼约 0~0.45（归一化后）

// 主高光：较大，左上角
uniform vec2  hl1_uv       = vec2(0.81, 0.38);  // 归一化眼睛 UV 内的位置
uniform float hl1_radius   = 0.2;                // 光点半径（UV 空间）
uniform float hl1_strength = 0.85;               // 亮度

// 副高光：较小
uniform vec2  hl2_uv       = vec2(0.16, 0.78);
uniform float hl2_radius   = 0.035;
uniform float hl2_strength = 0.4;

uniform vec3  highlight_color : source_color = vec3(1.0, 1.0, 1.0);

// 由 GDScript 控制：生气/悲伤时淡出
uniform float highlight_alpha : hint_range(0.0, 1.0) = 1.0;


void fragment() {
	vec4 base = texture(texture_albedo, UV);

	// 将 U 从 [0.135, 0.865] 归一化到 [0, 1]
	float u = (UV.x - 0.135) / (0.865 - 0.135);
	// 将 V 归一化：每只眼各占约 0.45 的区间，统一映射到 [0, 1]
	float v = fract(UV.y * 2.0) / 0.9;

	vec2 eye_uv = vec2(u, v);

	// 主高光
	float d1 = length(eye_uv - hl1_uv);
	float h1 = (1.0 - smoothstep(0.0, hl1_radius, d1)) * hl1_strength;

	// 副高光
	float d2 = length(eye_uv - hl2_uv);
	float h2 = (1.0 - smoothstep(0.0, hl2_radius, d2)) * hl2_strength;

	float hl = clamp(h1 + h2, 0.0, 1.0) * highlight_alpha;
	ALBEDO = mix(base.rgb, highlight_color, hl);
	ALPHA  = base.a;
}

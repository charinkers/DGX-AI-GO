// RobotDesignLoader.cs
// 放在 Unity 工程的 Assets/Scripts/ 下。
// 作用：把「设计交付」的 robot-design.json 加载并应用到仿真场景中的机器人预制体，
// 即「吐设计结果给机器人仿真场景，形成定制机器人的物理实现」。
// 契约定义见 schemas/robot-design.schema.json（v1）。

using UnityEngine;
using System.IO;

[System.Serializable] public class Appearance  { public string body_color; public string wing_type; public string body_shape; public string accessory; }
[System.Serializable] public class Personality { public string trait; public string catchphrase; public string voice_tone; }
[System.Serializable] public class Locomotion  { public string mode; public float max_speed; public string physics_profile; }
[System.Serializable] public class Safety      { public string role_boundaries; public bool content_filter; }

[System.Serializable]
public class RobotDesignSpec {
    public string ip_id;
    public string designer;
    public Appearance appearance;
    public Personality personality;
    public string[] expression_set;
    public Locomotion locomotion;
    public int battery;
    public Safety safety;
}

public class RobotDesignLoader : MonoBehaviour {
    public GameObject robotPrefab;
    public string specPath = "robot-design.json";  // 可来自 Web 预览导出 / harness 写回

    void Start() {
        var spec = LoadSpec(specPath);
        if (spec != null) ApplySpec(spec);
    }

    RobotDesignSpec LoadSpec(string path) {
        if (!File.Exists(path)) { Debug.LogWarning("未找到设计契约: " + path); return null; }
        return JsonUtility.FromJson<RobotDesignSpec>(File.ReadAllText(path));
    }

    void ApplySpec(RobotDesignSpec s) {
        GameObject bot = Instantiate(robotPrefab);

        // —— 外观：颜色 / 翅膀 / 性格标签 ——
        var rend = bot.GetComponentInChildren<Renderer>();
        if (rend != null && ColorUtility.TryParseHtmlString(s.appearance.body_color, out var c))
            rend.material.color = c;

        // —— 运动 / 物理实现：喂给 Unity 物理档位 ——
        var rb = bot.GetComponent<Rigidbody>();
        if (rb != null) {
            rb.mass = s.locomotion.physics_profile == "light" ? 0.5f
                    : s.locomotion.physics_profile == "heavy" ? 2.0f : 1.0f;
        }

        // —— 表情集：绑定 BlendShape（示意）——
        // foreach (var e in s.expression_set) { /* 设置对应 BlendShape 权重 */ }

        Debug.Log($"[定制机器人已加载] ip={s.ip_id} trait={s.personality.trait} " +
                  $"wing={s.appearance.wing_type} battery={s.battery} " +
                  $"role={s.safety.role_boundaries}");
    }
}

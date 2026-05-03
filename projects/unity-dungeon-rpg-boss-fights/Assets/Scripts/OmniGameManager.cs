using UnityEngine;

public class OmniGameManager : MonoBehaviour
{
    public string projectName = "unity-dungeon-rpg-boss-fights";
    public PlayerController player;
    public EnemyAI[] enemies;

    private void Start()
    {
        Debug.Log($"{projectName} initialized with {enemies.Length} enemies.");
    }

    private void Update()
    {
        if (player != null && player.Health <= 0)
        {
            Debug.Log("Player defeated. Reload the scene to retry.");
        }
    }
}

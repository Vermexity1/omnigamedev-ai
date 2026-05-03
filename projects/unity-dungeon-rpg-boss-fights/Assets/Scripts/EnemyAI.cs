using UnityEngine;

public class EnemyAI : MonoBehaviour
{
    public float health = 50f;
    public float moveSpeed = 2f;
    public float attackDamage = 8f;
    public float detectionRange = 10f;
    public bool isBoss;

    private Transform player;

    private void Start()
    {
        PlayerController controller = FindObjectOfType<PlayerController>();
        if (controller != null)
        {
            player = controller.transform;
        }
        if (isBoss)
        {
            health *= 4f;
            transform.localScale *= 1.8f;
        }
    }

    private void Update()
    {
        if (player == null || health <= 0f)
        {
            return;
        }

        float distance = Vector3.Distance(transform.position, player.position);
        if (distance < detectionRange)
        {
            Vector3 direction = (player.position - transform.position).normalized;
            transform.position += direction * moveSpeed * Time.deltaTime;
            transform.LookAt(player.position);
        }
    }

    public void Damage(float amount)
    {
        health -= amount;
        if (health <= 0f)
        {
            gameObject.SetActive(false);
        }
    }
}

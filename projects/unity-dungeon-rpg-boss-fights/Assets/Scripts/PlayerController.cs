using UnityEngine;

[RequireComponent(typeof(CharacterController))]
public class PlayerController : MonoBehaviour
{
    public float moveSpeed = 5f;
    public float attackRange = 2f;
    public float attackDamage = 25f;
    public float Health { get; private set; } = 100f;

    private CharacterController controller;

    private void Awake()
    {
        controller = GetComponent<CharacterController>();
    }

    private void Update()
    {
        float horizontal = Input.GetAxis("Horizontal");
        float vertical = Input.GetAxis("Vertical");
        Vector3 movement = new Vector3(horizontal, 0f, vertical);
        controller.SimpleMove(movement * moveSpeed);

        if (Input.GetKeyDown(KeyCode.Space))
        {
            Attack();
        }
    }

    public void Damage(float amount)
    {
        Health = Mathf.Max(0f, Health - amount);
    }

    private void Attack()
    {
        Collider[] hits = Physics.OverlapSphere(transform.position, attackRange);
        foreach (Collider hit in hits)
        {
            EnemyAI enemy = hit.GetComponent<EnemyAI>();
            if (enemy != null)
            {
                enemy.Damage(attackDamage);
            }
        }
    }
}

using UnityEngine;

public class LookAtDog : MonoBehaviour
{
    public Transform dog; // Reference to the dog's transform

    void Update()
    {
        if (dog != null)
        {
            // Make the camera look at the dog
            transform.LookAt(dog);
        }
    }
}
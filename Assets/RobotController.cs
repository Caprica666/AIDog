using UnityEngine;
public static class RobotEvents
{
    public static System.Action<int> OnTurnRobot; // angle in degreees
}

public class RobotController : MonoBehaviour
{
    // Subscribe to the OnTurnRobot event
    private void OnEnable()
    {
        RobotEvents.OnTurnRobot += TurnRobotAboutYAxis;
    }

    // Unsubscribe from the OnTurnRobot event
    private void OnDisable()
    {
        RobotEvents.OnTurnRobot -= TurnRobotAboutYAxis;
    }

    // Method to handle the rotation
    private void TurnRobotAboutYAxis(int angle)
    {
        transform.Rotate(0, angle, 0, Space.World);
        //StartCoroutine(RotateRobot(angle, speed));
    }

    // Coroutine to smoothly rotate the model
    private System.Collections.IEnumerator RotateRobot(float angle, float speed)
    {
        Quaternion startRotation = transform.rotation;
        Quaternion endRotation = Quaternion.Euler(0, transform.eulerAngles.y + angle, 0);
        float elapsedTime = 0;

        while (elapsedTime < 1f)
        {
            transform.rotation = Quaternion.Slerp(startRotation, endRotation, elapsedTime);
            elapsedTime += Time.deltaTime * speed;
            yield return null;
        }

        transform.rotation = endRotation; // Ensure final rotation is exact
    }
}

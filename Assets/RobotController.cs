using UnityEngine;
public static class RobotEvents
{
    public static System.Action<int> OnTurnRobot; // angle in degrees
    public static System.Action<int> OnSetRobotYAngle; // angle in degrees
}

public class RobotController : MonoBehaviour
{
    // Subscribe to the OnTurnRobot event
    private void OnEnable()
    {
        RobotEvents.OnTurnRobot += TurnRobotAboutYAxis;
        RobotEvents.OnSetRobotYAngle += SetRobotYAngle;
    }

    // Unsubscribe from the OnTurnRobot event
    private void OnDisable()
    {
        RobotEvents.OnTurnRobot -= TurnRobotAboutYAxis;
        RobotEvents.OnSetRobotYAngle -= SetRobotYAngle;
    }

    private void TurnRobotAboutYAxis(int angle)
    {
        var newY = transform.eulerAngles.y + angle;
        transform.eulerAngles = new Vector3(
            transform.eulerAngles.x,
            newY,
            transform.eulerAngles.z);
        //StartCoroutine(RotateRobot(angle, speed));
    }

    private void SetRobotYAngle(int newY)
    {
        transform.eulerAngles = new Vector3(
            transform.eulerAngles.x,
            newY,
            transform.eulerAngles.z
        );
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

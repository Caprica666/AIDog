using System;
using System.Threading;
using System.IO;
using Unity.VisualScripting.InputSystem;
using UnityEditor;
using UnityEngine;

public static class RobotEvents
{
    public static System.Action<float, float, EventWaitHandle> OnTurnRobot;
    public static System.Action<float, float, EventWaitHandle> OnSetRobotYAngle;
}

public class RobotController : MonoBehaviour
{
    private bool asyncRotation = true;
    private bool isRotating = false;

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

    private void TurnRobotAboutYAxis(float angle, float speed, EventWaitHandle waitHandle)
    {
        if (asyncRotation)
        {
            StartCoroutine(RotateYAxisRelative(angle, speed, waitHandle));
        }
        else
        {
            var newY = transform.eulerAngles.y + angle;
            transform.eulerAngles = new Vector3(transform.eulerAngles.x, newY, transform.eulerAngles.z);
            waitHandle.Set();                // Signal that the rotation is complete
        }
    }

    private void SetRobotYAngle(float newY, float speed, EventWaitHandle waitHandle)
    {
        if (asyncRotation)
        {
            StartCoroutine(RotateYAxisAbsolute(newY, speed, waitHandle)); // Speed is arbitrary here
        }
        else
        {
            transform.eulerAngles = new Vector3(transform.eulerAngles.x, newY, transform.eulerAngles.z);
            waitHandle.Set();                // Signal that the rotation is complete
        }
    }

    /*
     * Rotate the robot about the Y-axis to a specific angle.
     * If asyncRotation is true, it will rotate asynchronously.
     * If asyncRotation is false, it will set the angle immediately.
     *
     * @param newY The target Y angle in degrees.
     * @param speed The speed of rotation in degrees per second.
     * @param waitHandle An optional EventWaitHandle to signal when the rotation is complete.
     * @return An IEnumerator for coroutine execution if asyncRotation is true.
     */
    private System.Collections.IEnumerator RotateYAxisAbsolute(float newY, float speed, EventWaitHandle waitHandle)
    {
        Quaternion currentRot = transform.rotation;
        float angle = Math.Abs(newY - currentRot.eulerAngles.y);

        if (Math.Abs(angle) > 180)
        {
            angle = -angle; // Adjust for shortest rotation
        }
        yield return RotateYAxisRelative(angle, speed, waitHandle);
    }

    /*
     * Rotate the robot about the Y-axis a specified number of degrees.
     * If asyncRotation is true, it will rotate asynchronously.
     * If asyncRotation is false, it will set the angle immediately.
     *
     * @param newY The amount to turn in degrees.
     * @param speed The speed of rotation in degrees per second.
     * @param waitHandle An optional EventWaitHandle to signal when the rotation is complete.
     * @return An IEnumerator for coroutine execution if asyncRotation is true.
     */
    private System.Collections.IEnumerator RotateYAxisRelative(float angle, float speed, EventWaitHandle waitHandle)
    {
        if (isRotating)
        {
            Debug.Log($"Error - still rotating");
            yield break;
        }

        Quaternion currentRot = transform.rotation;
        float time = 0;
        float duration = Math.Abs(angle) / speed;
        float curY = transform.eulerAngles.y;
        float newY = curY + angle;
        Quaternion endRotation = Quaternion.Euler(currentRot.x, newY, currentRot.z);


        if (Math.Abs(angle) < 0.001f)
        {
            Debug.Log($"No rotation necessary");
            waitHandle.Set();
            yield return null;
        }
        Debug.Log($"Rotating robot {angle} degrees in {duration} seconds");
        isRotating = true;
        while (time < duration)
        {
            transform.rotation = Quaternion.Slerp(currentRot, endRotation, time / duration);
            time += Time.deltaTime;
            yield return null;
        }
        isRotating = false;
        transform.rotation = endRotation; // Ensure final rotation is exact
        Debug.Log($"Rotation complete current angle = {transform.eulerAngles.y}");
        waitHandle.Set();                // Signal that the rotation is complete
    }
}

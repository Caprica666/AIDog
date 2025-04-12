using UnityEngine;

public class CreateSubdividedPlane : MonoBehaviour
{
    public int subdivisions = 10; // Number of subdivisions for the plane

    void Start()
    {
        CreatePlane(subdivisions);
    }

    void CreatePlane(int subdivisions)
    {
        GameObject plane = new GameObject("SubdividedPlane");
        plane.AddComponent<MeshFilter>();
        plane.AddComponent<MeshRenderer>();

        Mesh mesh = new Mesh();
        plane.GetComponent<MeshFilter>().mesh = mesh;

        int resolution = subdivisions + 1;
        Vector3[] vertices = new Vector3[resolution * resolution];
        int[] triangles = new int[subdivisions * subdivisions * 6];
        Vector2[] uv = new Vector2[vertices.Length];

        // Create vertices and UVs
        for (int y = 0; y < resolution; y++)
        {
            for (int x = 0; x < resolution; x++)
            {
                int index = y * resolution + x;
                vertices[index] = new Vector3((float)x / subdivisions, 0, (float)y / subdivisions);
                uv[index] = new Vector2((float)x / subdivisions, (float)y / subdivisions);
            }
        }

        // Create triangles
        int triangleIndex = 0;
        for (int y = 0; y < subdivisions; y++)
        {
            for (int x = 0; x < subdivisions; x++)
            {
                int bottomLeft = y * resolution + x;
                int bottomRight = bottomLeft + 1;
                int topLeft = bottomLeft + resolution;
                int topRight = topLeft + 1;

                triangles[triangleIndex++] = bottomLeft;
                triangles[triangleIndex++] = topLeft;
                triangles[triangleIndex++] = topRight;

                triangles[triangleIndex++] = bottomLeft;
                triangles[triangleIndex++] = topRight;
                triangles[triangleIndex++] = bottomRight;
            }
        }

        // Assign mesh data
        mesh.vertices = vertices;
        mesh.triangles = triangles;
        mesh.uv = uv;
        mesh.RecalculateNormals();

        // Add a default material
        plane.GetComponent<MeshRenderer>().material = new Material(Shader.Find("Standard"));
    }
}
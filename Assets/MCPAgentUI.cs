using UnityEngine;
using UnityEngine.UI;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using System.Diagnostics;

public class MCPAgentUI : MonoBehaviour
{
    public Button startButton;
    public Button stopButton;
    public InputField instructionInput;
    public Button sendInstructionButton;
    public Text responseText;

    private HttpClient httpClient;
    private Process mcpAgentProcess;

    void Start()
    {
        httpClient = new HttpClient();

        startButton.onClick.AddListener(StartAgent);
        stopButton.onClick.AddListener(StopAgent);
        sendInstructionButton.onClick.AddListener(SendInstruction);
    }

    async void StartAgent()
    {
        if (mcpAgentProcess == null || mcpAgentProcess.HasExited)
        {
            await Task.Run(() =>
            {
                ProcessStartInfo startInfo = new ProcessStartInfo
                {
                    FileName = "python",
                    Arguments = "UnityMCPAgent/agent.py",
                    WorkingDirectory = @"c:\\projects\\Unity\\AIDog",
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true
                };

                mcpAgentProcess = Process.Start(startInfo);
            });

            responseText.text = "Agent started successfully.";
        }
        else
        {
            responseText.text = "Agent is already running.";
        }
    }

    void StopAgent()
    {
        if (mcpAgentProcess != null && !mcpAgentProcess.HasExited)
        {
            mcpAgentProcess.Kill();
            mcpAgentProcess = null;
            responseText.text = "Agent stopped successfully.";
        }
        else
        {
            responseText.text = "Agent is not running.";
        }
    }

    async void SendInstruction()
    {
        string instruction = instructionInput.text;
        if (string.IsNullOrEmpty(instruction))
        {
            responseText.text = "Please enter an instruction.";
            return;
        }

        string url = "http://localhost:8000/process_user_instruction"; // Replace with actual instruction endpoint
        var content = new StringContent($"{{\"instruction\":\"{instruction}\"}}", Encoding.UTF8, "application/json");

        HttpResponseMessage response = await httpClient.PostAsync(url, content);
        if (response.IsSuccessStatusCode)
        {
            string result = await response.Content.ReadAsStringAsync();
            responseText.text = $"Response: {result}";
        }
        else
        {
            responseText.text = "Failed to send instruction.";
        }
    }

    void OnDestroy()
    {
        httpClient.Dispose();
    }
}
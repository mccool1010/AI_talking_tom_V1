# Generates the 12 spoken test phrases used by bench_pipeline.py
# (16 kHz mono WAV + reference transcript) with the built-in Windows voices.
# Usage: powershell -ExecutionPolicy Bypass -File benchmarks\make_inputs.ps1

$out = Join-Path $PSScriptRoot "data\inputs"
New-Item -ItemType Directory -Force $out | Out-Null
Add-Type -AssemblyName System.Speech

$lines = @(
    "Hi Tom, how are you doing today?",
    "My name is Hari and I study computer science.",
    "I really love playing football with my friends on weekends.",
    "What do you like to eat for breakfast?",
    "I had a really stressful exam this morning.",
    "Do you remember what sport I like?",
    "I am building a robot for my college project.",
    "Can you tell me a funny joke about cats?",
    "I hate waking up early on Monday mornings.",
    "What do you see around me right now?",
    "My sister is visiting us next week from Bangalore.",
    "Goodnight Tom, I am going to sleep now."
)

$format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(
    16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,
    [System.Speech.AudioFormat.AudioChannel]::Mono)
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
Write-Host "Voices:" ($synth.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name })

for ($i = 0; $i -lt $lines.Count; $i++) {
    $name = "{0:D2}" -f $i
    Write-Progress -Activity "Generating test phrases" -Status $lines[$i] -PercentComplete (100 * $i / $lines.Count)
    $synth.SetOutputToWaveFile((Join-Path $out "$name.wav"), $format)
    $synth.Speak($lines[$i])
    Set-Content -Path (Join-Path $out "$name.txt") -Value $lines[$i] -Encoding ascii
}
$synth.Dispose()
Write-Host "Wrote $($lines.Count) phrases to $out"

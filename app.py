from io import StringIO
import gradio as gr

from utils import write_vtt
import whisper

import ffmpeg

#import os
#os.system("pip install git+https://github.com/openai/whisper.git")

# Limitations (set to -1 to disable)
INPUT_AUDIO_MAX_DURATION = 120 # seconds

LANGUAGES = [
    "English",
    "Chinese",
    "German",
    "Spanish",
    "Russian",
    "Korean",
    "French",
    "Japanese",
    "Portuguese",
    "Turkish",
    "Polish",
    "Catalan",
    "Dutch",
    "Arabic",
    "Swedish",
    "Italian",
    "Indonesian",
    "Hindi",
    "Finnish",
    "Vietnamese",
    "Hebrew",
    "Ukrainian",
    "Greek",
    "Malay",
    "Czech",
    "Romanian",
    "Danish",
    "Hungarian",
    "Tamil",
    "Norwegian",
    "Thai",
    "Urdu",
    "Croatian",
    "Bulgarian",
    "Lithuanian",
    "Latin",
    "Maori",
    "Malayalam",
    "Welsh",
    "Slovak",
    "Telugu",
    "Persian",
    "Latvian",
    "Bengali",
    "Serbian",
    "Azerbaijani",
    "Slovenian",
    "Kannada",
    "Estonian",
    "Macedonian",
    "Breton",
    "Basque",
    "Icelandic",
    "Armenian",
    "Nepali",
    "Mongolian",
    "Bosnian",
    "Kazakh",
    "Albanian",
    "Swahili",
    "Galician",
    "Marathi",
    "Punjabi",
    "Sinhala",
    "Khmer",
    "Shona",
    "Yoruba",
    "Somali",
    "Afrikaans",
    "Occitan",
    "Georgian",
    "Belarusian",
    "Tajik",
    "Sindhi",
    "Gujarati",
    "Amharic",
    "Yiddish",
    "Lao",
    "Uzbek",
    "Faroese",
    "Haitian Creole",
    "Pashto",
    "Turkmen",
    "Nynorsk",
    "Maltese",
    "Sanskrit",
    "Luxembourgish",
    "Myanmar",
    "Tibetan",
    "Tagalog",
    "Malagasy",
    "Assamese",
    "Tatar",
    "Hawaiian",
    "Lingala",
    "Hausa",
    "Bashkir",
    "Javanese",
    "Sundanese"
]

model_cache = dict()

def greet(modelName, languageName, uploadFile, microphoneData, task):
    source = uploadFile if uploadFile is not None else microphoneData
    selectedLanguage = languageName.lower() if len(languageName) > 0 else None
    selectedModel = modelName if modelName is not None else "base"

    if INPUT_AUDIO_MAX_DURATION > 0:
        # Calculate audio length
        audioDuration = ffmpeg.probe(source)["format"]["duration"]
        
        if float(audioDuration) > INPUT_AUDIO_MAX_DURATION:
            return ("[ERROR]: Maximum audio file length is " + str(INPUT_AUDIO_MAX_DURATION) + "s, file was " + str(audioDuration) + "s"), "[ERROR]"

    model = model_cache.get(selectedModel, None)
    
    if not model:
        model = whisper.load_model(selectedModel)
        model_cache[selectedModel] = model

    result = model.transcribe(source, language=selectedLanguage, task=task)

    segmentStream = StringIO()
    write_vtt(result["segments"], file=segmentStream)
    segmentStream.seek(0)

    return result["text"], segmentStream.read()

ui_description = "Whisper is a general-purpose speech recognition model. It is trained on a large dataset of diverse " 
ui_description += " audio and is also a multi-task model that can perform multilingual speech recognition "
ui_description += " as well as speech translation and language identification. "

if INPUT_AUDIO_MAX_DURATION > 0:
    ui_description += "\n\n" + "Max audio file length: " + str(INPUT_AUDIO_MAX_DURATION) + " s"

demo = gr.Interface(fn=greet, description=ui_description, inputs=[
    gr.Dropdown(choices=["tiny", "base", "small", "medium", "large"], value="medium", label="Model"),
    gr.Dropdown(choices=sorted(LANGUAGES), label="Language"),
    gr.Audio(source="upload", type="filepath", label="Upload Audio"), 
    gr.Audio(source="microphone", type="filepath", label="Microphone Input"),
    gr.Dropdown(choices=["transcribe", "translate"], label="Task"),
], outputs=[gr.Text(label="Transcription"), gr.Text(label="Segments")])

demo.launch()   
import re
from typing import Iterator

from io import StringIO
import os
import pathlib
import tempfile

# External programs
import whisper
import ffmpeg

# UI
import gradio as gr
from download import downloadUrl

from utils import slugify, write_srt, write_vtt

# Limitations (set to -1 to disable)
DEFAULT_INPUT_AUDIO_MAX_DURATION = 600 # seconds

# Whether or not to automatically delete all uploaded files, to save disk space
DELETE_UPLOADED_FILES = True

# Gradio seems to truncate files without keeping the extension, so we need to truncate the file prefix ourself 
MAX_FILE_PREFIX_LENGTH = 17

LANGUAGES = [ 
 "English", "Chinese", "German", "Spanish", "Russian", "Korean", 
 "French", "Japanese", "Portuguese", "Turkish", "Polish", "Catalan", 
 "Dutch", "Arabic", "Swedish", "Italian", "Indonesian", "Hindi", 
 "Finnish", "Vietnamese", "Hebrew", "Ukrainian", "Greek", "Malay", 
 "Czech", "Romanian", "Danish", "Hungarian", "Tamil", "Norwegian", 
 "Thai", "Urdu", "Croatian", "Bulgarian", "Lithuanian", "Latin", 
 "Maori", "Malayalam", "Welsh", "Slovak", "Telugu", "Persian", 
 "Latvian", "Bengali", "Serbian", "Azerbaijani", "Slovenian", 
 "Kannada", "Estonian", "Macedonian", "Breton", "Basque", "Icelandic", 
 "Armenian", "Nepali", "Mongolian", "Bosnian", "Kazakh", "Albanian",
 "Swahili", "Galician", "Marathi", "Punjabi", "Sinhala", "Khmer", 
 "Shona", "Yoruba", "Somali", "Afrikaans", "Occitan", "Georgian", 
 "Belarusian", "Tajik", "Sindhi", "Gujarati", "Amharic", "Yiddish", 
 "Lao", "Uzbek", "Faroese", "Haitian Creole", "Pashto", "Turkmen", 
 "Nynorsk", "Maltese", "Sanskrit", "Luxembourgish", "Myanmar", "Tibetan",
 "Tagalog", "Malagasy", "Assamese", "Tatar", "Hawaiian", "Lingala", 
 "Hausa", "Bashkir", "Javanese", "Sundanese"
]

model_cache = dict()

class UI:
    def __init__(self, inputAudioMaxDuration):
        self.inputAudioMaxDuration = inputAudioMaxDuration

    def transcribeFile(self, modelName, languageName, urlData, uploadFile, microphoneData, task):
        source, sourceName = getSource(urlData, uploadFile, microphoneData)
        
        try:
            selectedLanguage = languageName.lower() if len(languageName) > 0 else None
            selectedModel = modelName if modelName is not None else "base"

            if self.inputAudioMaxDuration > 0:
                # Calculate audio length
                audioDuration = ffmpeg.probe(source)["format"]["duration"]
                
                if float(audioDuration) > self.inputAudioMaxDuration:
                    return ("[ERROR]: Maximum audio file length is " + str(self.inputAudioMaxDuration) + "s, file was " + str(audioDuration) + "s"), "[ERROR]"

            model = model_cache.get(selectedModel, None)
            
            if not model:
                model = whisper.load_model(selectedModel)
                model_cache[selectedModel] = model

            # The results
            result = model.transcribe(source, language=selectedLanguage, task=task)

            text = result["text"]

            language = result["language"]
            languageMaxLineWidth = getMaxLineWidth(language)

            print("Max line width " + str(languageMaxLineWidth))
            vtt = getSubs(result["segments"], "vtt", languageMaxLineWidth)
            srt = getSubs(result["segments"], "srt", languageMaxLineWidth)

            # Files that can be downloaded
            downloadDirectory = tempfile.mkdtemp()
            filePrefix = slugify(sourceName, allow_unicode=True)

            download = []
            download.append(createFile(srt, downloadDirectory, filePrefix + "-subs.srt"));
            download.append(createFile(vtt, downloadDirectory, filePrefix + "-subs.vtt"));
            download.append(createFile(text, downloadDirectory, filePrefix + "-transcript.txt"));

            return download, text, vtt

        finally:
            # Cleanup source
            if DELETE_UPLOADED_FILES:
                print("Deleting source file " + source)
                os.remove(source)


def getMaxLineWidth(language: str) -> int:
    if (language == "ja" or language == "zh"):
        # Chinese characters and kana are wider, so limit line length to 40 characters
        return 40
    else:
        # TODO: Add more languages
        # 80 latin characters should fit on a 1080p/720p screen
        return 80

def getSource(urlData, uploadFile, microphoneData):
    if urlData:
        # Download from YouTube
        source = downloadUrl(urlData)
    else:
        # File input
        source = uploadFile if uploadFile is not None else microphoneData

    file_path = pathlib.Path(source)
    sourceName = file_path.stem[:MAX_FILE_PREFIX_LENGTH] + file_path.suffix

    return source, sourceName

def createFile(text: str, directory: str, fileName: str) -> str:
    # Write the text to a file
    with open(os.path.join(directory, fileName), 'w+', encoding="utf-8") as file:
        file.write(text)

    return file.name

def getSubs(segments: Iterator[dict], format: str, maxLineWidth: int) -> str:
    segmentStream = StringIO()

    if format == 'vtt':
        write_vtt(segments, file=segmentStream, maxLineWidth=maxLineWidth)
    elif format == 'srt':
        write_srt(segments, file=segmentStream, maxLineWidth=maxLineWidth)
    else:
        raise Exception("Unknown format " + format)

    segmentStream.seek(0)
    return segmentStream.read()
    

def createUi(inputAudioMaxDuration, share=False, server_name: str = None):
    ui = UI(inputAudioMaxDuration)

    ui_description = "Whisper is a general-purpose speech recognition model. It is trained on a large dataset of diverse " 
    ui_description += " audio and is also a multi-task model that can perform multilingual speech recognition "
    ui_description += " as well as speech translation and language identification. "

    if inputAudioMaxDuration > 0:
        ui_description += "\n\n" + "Max audio file length: " + str(inputAudioMaxDuration) + " s"

    demo = gr.Interface(fn=ui.transcribeFile, description=ui_description, inputs=[
        gr.Dropdown(choices=["tiny", "base", "small", "medium", "large"], value="medium", label="Model"),
        gr.Dropdown(choices=sorted(LANGUAGES), label="Language"),
        gr.Text(label="URL (YouTube, etc.)"),
        gr.Audio(source="upload", type="filepath", label="Upload Audio"), 
        gr.Audio(source="microphone", type="filepath", label="Microphone Input"),
        gr.Dropdown(choices=["transcribe", "translate"], label="Task"),
    ], outputs=[
        gr.File(label="Download"),
        gr.Text(label="Transcription"), 
        gr.Text(label="Segments")
    ])

    demo.launch(share=share, server_name=server_name)   

if __name__ == '__main__':
    createUi(DEFAULT_INPUT_AUDIO_MAX_DURATION)
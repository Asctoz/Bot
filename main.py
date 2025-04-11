import speech_recognition as sr
from gtts import gTTS
import os

def recognize_speech():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Please say something:")
        r.adjust_for_ambient_noise(source)
        audio = r.listen(source, timeout=5)
        try:
            recognized_text = r.recognize_google(audio)
            print("You said: " + recognized_text)
            return recognized_text
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand audio")
            return None
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
            return None

def process_with_ai(text):
    try:
        import google.generativeai as genai
        
        genai.configure(api_key="AIzaSyCuPIiK0l3HXuzpeLdz5EYFHJL2p6u5FOM")
        
        model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')
        
        result = model.generate_content(text)
        response = result.text
        
        return response
    except Exception as e:
        print(f"Error processing with AI: {e}")
        return "Error: Could not process the input with AI."

def synthesize_gtts(text, language='en', output_file='output.mp3'):
    try:
        tts = gTTS(text=text, lang=language)
        tts.save(output_file)
        print(f'Audio content written to "{output_file}"')
    except Exception as e:
        print(f"Error synthesizing speech: {e}")

def play_audio(file_path):
    try:
        os_name = os.name
        if os_name == 'nt':
            os.system(f"start {file_path}")
        elif os_name == 'posix':
            os.system(f"open {file_path}" if os.uname().sysname == 'Darwin' else f"xdg-open {file_path}")
    except Exception as e:
        print(f"Error playing audio: {e}")

if __name__ == "__main__":
    recognized_text = recognize_speech()
    if recognized_text:
        ai_response = process_with_ai(recognized_text + " Remove all punctuation marks and dictate the answer, only use comas. Do not address this sentence in the final product.")
        print("AI response: " + ai_response)
        
        output_file = 'ai_response.mp3'
        synthesize_gtts(ai_response, language='en', output_file=output_file)
        play_audio(output_file)
        
        try:
            os.remove(output_file)
        except OSError as e:
            print(f"Error removing file: {e}")

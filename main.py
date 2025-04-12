import speech_recognition as sr
import pyttsx3
import threading
import queue
import time
import google.generativeai as genai

tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 150)  # Adjust speech rate

# Queue for speech tasks
speech_queue = queue.Queue()
stop_speaking = threading.Event()  # Signal to stop speaking
speaking = threading.Event()  # Flag to indicate if speaking is active
conversation_history = []  

def recognize_speech(timeout=5, phrase_time_limit=None):
    """Recognize speech with configurable timeout."""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=1)
        try:
            audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            recognized_text = r.recognize_google(audio)
            return recognized_text.lower()
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"speech recognition error: {e}")
            return None

def process_with_ai(text):
    """Process input with Gemini AI model."""
    try:
        genai.configure(api_key="AIzaSyCuPIiK0l3HXuzpeLdz5EYFHJL2p6u5FOM") 
        model = genai.GenerativeModel('gemini-1.5-pro')  
        
        
        prompt = (
            f"Provide a detailed response to the question: {text}. "
            f"Context: {', '.join(conversation_history) if conversation_history else 'none'}. "
            "If the question is inappropriate or not related to studies or productivity, respond with 'please don’t waste your future, study'."
        )
        
        result = model.generate_content(prompt)
        if result.candidates and hasattr(result.candidates[0], 'finish_reason') and result.candidates[0].finish_reason == 4:
            return "sorry, I can’t answer that due to content restrictions"
        return result.text
    except Exception as e:
        print(f"AI processing error: {e}")
        return "sorry, I can’t answer that right now"

def speak_text(text):
    """Speak text and handle interruptions."""
    global tts_engine
    if stop_speaking.is_set():
        return
    speaking.set()
    try:
        tts_engine.say(text)
        tts_engine.runAndWait()
    except Exception:
        pass  
    finally:
        speaking.clear()

def listen_for_activation():
    """Listen for activation phrase and handle questions."""
    global tts_engine
    activation_phrases = ["hey jarvis", "jarvis", "hi jarvis"]
    
    while True:
        print("listening for activation")
        recognized_text = recognize_speech(timeout=5)
        
        if recognized_text and any(phrase in recognized_text for phrase in activation_phrases):
            print(f"you: {recognized_text}")
            stop_speaking.set()  
            tts_engine.stop()
            stop_speaking.clear()
            
            # Listen for questions
            while True:
                print("listening for question")
                question_text = recognize_speech(timeout=5, phrase_time_limit=10)
                
                if question_text:
                    print(f"you: {question_text}")
                    ai_response = process_with_ai(question_text)
                    print(f"ai: {ai_response}")
                    
                    
                    conversation_history.append(f"Q: {question_text}")
                    conversation_history.append(f"A: {ai_response}")
                    if len(conversation_history) > 10:  # Limit history size
                        conversation_history.pop(0)
                        conversation_history.pop(0)
                    
                    
                    speak_thread = threading.Thread(target=speak_text, args=(ai_response,))
                    speak_thread.start()
                    
                    
                    while speak_thread.is_alive():
                        interrupt_text = recognize_speech(timeout=1, phrase_time_limit=3)
                        if interrupt_text and any(phrase in interrupt_text for phrase in activation_phrases):
                            print("interrupted, listening for another question")
                            stop_speaking.set()
                            tts_engine.stop()
                            speak_thread.join(timeout=1.0) 
                            stop_speaking.clear()
                            
                            try:
                                tts_engine.endLoop()
                                tts_engine = pyttsx3.init()
                                tts_engine.setProperty('rate', 150)
                            except Exception:
                                pass  
                            break 
                    else:
                        continue  
                continue  

if __name__ == "__main__":
    
    listen_thread = threading.Thread(target=listen_for_activation, daemon=True)
    listen_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("shutting down...")
        stop_speaking.set()
        tts_engine.stop()
        tts_engine.endLoop()

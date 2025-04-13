    #Bot

      a physical study companion for students to help in covering topics, clearing doubts and overcoming problems with your own friendly robot.

      coems.


## import pyaudio

p = pyaudio.PyAudio()
for i in range(p.get_device_count()):
    dev = p.get_device_info_by_index(i)
    if dev['maxInputChannels'] > 0:
        print(f"[{i}] {dev['name']}")
stream = p.open(format=pyaudio.paInt16,
                channels=1,
                rate=44100,
                input=True,
                input_device_index=YOUR_MIC_INDEX,
                frames_per_buffer=1024)

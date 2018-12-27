import subprocess, time, os, sys
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty,\
    ObjectProperty, BooleanProperty, StringProperty
from kivy.vector import Vector
from kivy.clock import Clock
from kivy.uix.image import Image
from KivyQueueClass import KivyQueue
import threading
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from collections import defaultdict
from kivy.core.window import Window
Window.clearcolor = (1, 1, 1, 1)
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.loader import Loader
from kivy.uix.textinput import TextInput
import json


d = defaultdict(list)


scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']



class Erg(Widget):
    connected = BooleanProperty(False)

    def change_text(self, _text):

        if 'Dist' in _text:
            self.disthist.append(int(_text[_text.find('Distance: ')+len('Distance: '):]))
            self.ldist.text = str(self.disthist[-1]) + ' m'
        else:
            self.speedhist.append(int(_text[_text.find('Speed: ')+len('Speed: '):_text.find(' Split:')]))
            self.lspeed.text = str(self.speedhist[-1]) +' m/s'

            self.ratehist.append(int(_text[_text.find('Rate: ')+len('Rate: '):]))
            self.lrate.text = str(self.ratehist[-1]) +' str/min'

            self.splithist.append(_text[_text.find('Speed: ')+len('Speed: '):_text.find(' Split:')])
            self.lsplit.text = self.splithist[-1]
        print(self.speedhist)

    def update_status(self, _connected):
        if _connected:
            self.speedhist = []
            self.splithist = []
            self.ratehist = []
            self.disthist = []
            self.change_text('Speed: 0 Split: 0:00 Stroke Rate: 0')
            self.connected = True
            self.limg.source  = 'images/erg_online.png'
        else:
            self.change_text('')
            self.connected = False
            self.limg.source  = 'images/erg_offline.png'



class ErgMonitorBase(Screen):
    pass

class WorkoutScores(Screen):
    pass

class Settings(Screen):
    pass

class ErgMonitorApp(App):


    with open('settings.json') as f:
        savedict = json.load(f)
    PMDict = {v: k for k, v in savedict.items()}

    stop = threading.Event()
    q = KivyQueue(notify_func=None)

    def process(self):
        data = self.q.get()
        pmid = data[0]
        pmdata = data[1]
        curerg = None
        if 'FIN' in pmdata:
            time = pmdata[pmdata.find('Time: ')+len('Time: '):pmdata.find(' Distance')]
            distance = pmdata[pmdata.find('Distance: ')+len('Distance: '):pmdata.find(' Avg')]
            avg_split = pmdata[pmdata.find('Avg Split: ')+len('Avg Split: '):]
            d[self.PMdict[pmid][-1]].append((time, distance, avg_split))
            self.scores.tableList.data.insert(1,{'erg': self.PMdict[pmid][-1], 'time': str(time), 'dist': str(distance), 'avg_split': str(avg_split)})
        try:
            if 'CON' in pmdata:
                getattr(self.monitor, self.PMdict[pmid]).update_status(1)
            if 'DIS' in pmdata:
                getattr(self.monitor, self.PMdict[pmid]).update_status(0)
            if 'MON' in pmdata:
                getattr(self.monitor, self.PMdict[pmid]).change_text(pmdata[4:])
        except:
            pass

    def start_update_thread(self):
        self.scores.tableList.data.insert(0,{'erg': 'Erg', 'time': 'Time', 'dist': 'Dist', 'avg_split': 'Avg Splt'})
        self.q.notify_func = self.process
        t = threading.Thread(target=self.update_thread)
        t.daemon = True
        t.start()

    def update_thread(self):
        cmd = ["node", "erg_noble.js"]

        p = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)

        for line in iter(p.stdout.readline, b''):

            if self.stop.is_set():
                # Stop running this thread so the main Python process can exit.
                return

            print(line.rstrip().decode("utf-8"))
            s = line.rstrip().decode("utf-8")
            self.q.put(s[:13], s[13:])

    def on_stop(self):
        # The Kivy event loop is about to stop, set a stop signal;
        # otherwise the app window will close, but the Python process will
        # keep running until all secondary threads exit.
        self.root.stop.set()

    def save(self):
        self.savedict['erg1'] = self.settings.erg1.text
        self.savedict['erg2'] = self.settings.erg2.text
        self.savedict['erg3'] = self.settings.erg3.text
        self.savedict['erg4'] = self.settings.erg4.text
        self.savedict['erg5'] = self.settings.erg5.text
        self.savedict['erg6'] = self.settings.erg6.text
        self.savedict['erg7'] = self.settings.erg7.text
        self.savedict['erg8'] = self.settings.erg8.text

        self.PMdict = {v: k for k, v in self.savedict.items()}
        with open('settings.json', 'w') as outfile:
            json.dump(self.savedict, outfile)

    def upload(self):
        # try:
        creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
        client = gspread.authorize(creds)
        sheet = client.open("Erg Scores Test").sheet1
        for k,v in d.items():
            row = ['Erg ID']
            row += ['Time', 'Distance', 'Avg Split']*len(v)
            sheet.delete_row(1)
            sheet.insert_row(row, 1)
            break

        counter = 1
        for k,v in d.items():
            counter += 1
            row = [k]
            for a,b,c in v:
                row += [a,b,c]
            sheet.delete_row(counter)
            sheet.insert_row(row, counter)
            print('Uploaded')


    def build(self):
        Window.minimum_height = 600
        Window.minimum_width = 800
        #Window.borderless = 1
        sm = ScreenManager(transition=NoTransition())
        self.settings = Settings(name='settings')
        self.monitor = ErgMonitorBase(name='monitor')
        self.scores = WorkoutScores(name='scores')
        self.start_update_thread()
        sm.add_widget(self.monitor)
        sm.add_widget(self.scores)
        sm.add_widget(self.settings)

        return sm


if __name__ == '__main__':
    ErgMonitorApp().run()

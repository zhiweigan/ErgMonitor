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


d = defaultdict(list)

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']



class Erg(Widget):
    connected = BooleanProperty(False)
    speed = StringProperty('0')
    split = StringProperty('0:00')
    rate = StringProperty('0')

    def change_text(self, _text):
        self.ltext.text = _text

    def update_status(self, _connected):
        if _connected:
            self.change_text('Speed: 0 Split: 0:00 Stroke Rate: 0')
            self.connected = True
            self.limg.source  = 'erg_online.png'
        else:
            self.change_text('')
            self.connected = False
            self.limg.source  = 'erg_offline.png'



class ErgMonitorBase(Widget):

    stop = threading.Event()

    erg1 = ObjectProperty(None)
    erg2 = ObjectProperty(None)
    erg3 = ObjectProperty(None)
    erg4 = ObjectProperty(None)
    erg5 = ObjectProperty(None)
    erg6 = ObjectProperty(None)
    erg7 = ObjectProperty(None)
    erg8 = ObjectProperty(None)
    q = KivyQueue(notify_func=None)

    PMdict = {
    'PM5 430500339':'erg1',
    'PM5 430504875':'erg2',
    'PM5 430503904':'erg3',
    'PM5 430503899':'erg4',
    'PM5 430503944':'erg5',
    'PM5 430503892':'erg6',
    'PM5 430568518':'erg7',
    'PM5 430074445':'erg8'
    }

    def start_update_thread(self):
        self.tableList.data.insert(0,{'erg': 'Erg', 'time': 'Time', 'dist': 'Dist', 'avg_split': 'Avg Splt'})
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
            self.tableList.data.insert(1,{'erg': self.PMdict[pmid][-1], 'time': str(time), 'dist': str(distance), 'avg_split': str(avg_split)})

        try:
            if 'CON' in pmdata:
                getattr(self, self.PMdict[pmid]).update_status(1)
            if 'DIS' in pmdata:
                getattr(self, self.PMdict[pmid]).update_status(0)
            if 'MON' in pmdata:
                getattr(self, self.PMdict[pmid]).change_text(pmdata[4:])
        except:
            pass


class ErgMonitorApp(App):

    def on_stop(self):
        # The Kivy event loop is about to stop, set a stop signal;
        # otherwise the app window will close, but the Python process will
        # keep running until all secondary threads exit.
        self.root.stop.set()

    def upload(self):
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
        monitor = ErgMonitorBase()
        monitor.start_update_thread()
        #monitor.init_erg()
        #Clock.schedule_interval(monitor.update, 1.0 / 60.0)
        return monitor


if __name__ == '__main__':
    ErgMonitorApp().run()
import subprocess, time, os, sys
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import ObjectProperty, BooleanProperty
from kivy.clock import Clock
from KivyQueueClass import KivyQueue
import threading
import atexit
import datetime
from collections import defaultdict
from kivy.core.window import Window
Window.clearcolor = (1, 1, 1, 1)
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
import json
from kivy.garden.graph import Graph, MeshLinePlot
import socket
import numpy as np
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import webbrowser

scores = defaultdict(list)

gauth = GoogleAuth()
gauth.LoadCredentialsFile("credentials.json")
if gauth.credentials is None:
    gauth.LocalWebserverAuth()
elif gauth.access_token_expired:
    # Refresh them if expired
    gauth.Refresh()
else:
    gauth.Authorize()
gauth.SaveCredentialsFile("credentials.json")
drive = GoogleDrive(gauth)


class Erg(Widget):
    connected = BooleanProperty(False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.speedhist = []
        self.splithist = []
        self.ratehist = []
        self.disthist = []
        self.start_time = time.time()

    def change_text(self, _text):
        curtime = time.time()

        if 'Dist' in _text:
            self.disthist.append((curtime-self.start_time, int(_text[_text.find('Distance: ')+len('Distance: '):])))
            self.ldist.text = str(self.disthist[-1][1]) + ' m'
        else:
            self.speedhist.append((curtime-self.start_time, float(_text[_text.find('Speed: ')+len('Speed: '):_text.find(' Split:')-3])))
            self.lspeed.text = str(self.speedhist[-1][1]) +' m/s'

            self.ratehist.append((curtime-self.start_time,int(_text[_text.find('Rate: ')+len('Rate: '):])))
            self.lrate.text = str(self.ratehist[-1][1]) +' str/min'

            self.splithist.append((curtime-self.start_time,_text[_text.find('Split: ')+len('Split: '):_text.find(' Stroke')]))
            self.lsplit.text = self.splithist[-1][1]

    def update_status(self, _connected):
        if _connected:

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

class ErgGraph(Widget):
    pass



class GraphScreen(Screen):
    erg1 = ObjectProperty(None)
    erg2 = ObjectProperty(None)
    erg3 = ObjectProperty(None)
    erg4 = ObjectProperty(None)
    erg5 = ObjectProperty(None)
    erg6 = ObjectProperty(None)
    erg7 = ObjectProperty(None)
    erg8 = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.erg1.ergNum.text = 'Erg 1'
        self.erg2.ergNum.text = 'Erg 2'
        self.erg3.ergNum.text = 'Erg 3'
        self.erg4.ergNum.text = 'Erg 4'
        self.erg5.ergNum.text = 'Erg 5'
        self.erg6.ergNum.text = 'Erg 6'
        self.erg7.ergNum.text = 'Erg 7'
        self.erg8.ergNum.text = 'Erg 8'
        self.rateplots = []
        self.speedplots = []
        self.starttime = time.time()

        for i in range(8):
            rate = MeshLinePlot(color=[0, 1, 0, 1])
            speed = MeshLinePlot(color=[1, 0, 0, 1])
            self.rateplots.append(rate)
            self.speedplots.append(speed)
            getattr(self, 'erg'+str(i+1)).graph.add_plot(self.rateplots[i])
            getattr(self, 'erg' + str(i + 1)).graph.add_plot(self.speedplots[i])


    def update_graphs(self, *args):
        for i in range(8):
            self.rateplots[i].points = [(j,int(x[1])) for j,x in enumerate(getattr(app.monitor, 'erg'+str(i+1)).ratehist[1:])]
            self.speedplots[i].points = [(j,int(x[1])) for j,x in enumerate(getattr(app.monitor, 'erg' + str(i + 1)).speedhist[1:])]
            if len(self.rateplots[i].points) > 0 and self.rateplots[i].points[-1][0] > 100: # TEST
                getattr(self, 'erg' + str(i + 1)).graph.xmin = self.rateplots[i][-1][0]-100
                getattr(self, 'erg' + str(i + 1)).graph.xmax = self.rateplots[i][-1][0]


    def save_graph(self):
        for i in range(8):
            np.savetxt('./stroke_data/erg'+str(i+1)+'_rate.csv', getattr(app.monitor, 'erg'+str(i+1)).ratehist, delimiter=',', fmt='%s')
            np.savetxt('./stroke_data/erg' + str(i + 1) + '_speed.csv', getattr(app.monitor, 'erg' + str(i + 1)).speedhist, delimiter=',', fmt='%s')


class ErgMonitorApp(App):


    with open('settings.json') as f:
        savedict = json.load(f)
    PMdict = {v: k for k, v in savedict.items()}

    stop = threading.Event()
    q = KivyQueue(notify_func=None)

    def process(self):
        data = self.q.get()
        pmid = data[0]
        pmdata = data[1]
        if 'FIN' in pmdata:
            time = pmdata[pmdata.find('Time: ')+len('Time: '):pmdata.find(' Distance')]
            distance = pmdata[pmdata.find('Distance: ')+len('Distance: '):pmdata.find(' Avg')]
            avg_split = pmdata[pmdata.find('Avg Split: ')+len('Avg Split: '):]
            scores[self.PMdict[pmid][-1]].append((time, distance, avg_split))
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
            #traceback.print_exc()

    def start_update_thread(self):
        self.scores.tableList.data.insert(0,{'erg': 'Erg', 'time': 'Time', 'dist': 'Dist', 'avg_split': 'Avg Splt'})
        self.q.notify_func = self.process
        t = threading.Thread(target=self.update_thread)
        t.daemon = True
        t.start()

    def restart_backend(self):
        self.p.kill()

        cmd = ["node", "erg_noble.js"]

        self.p = subprocess.Popen(cmd,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)

    def update_thread(self):
        cmd = ["node", "erg_noble.js"]

        self.p = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)

        UDP_IP = "127.0.0.1"
        UDP_PORT = 6900
        sock = socket.socket(socket.AF_INET,  socket.SOCK_DGRAM)
        sock.bind((UDP_IP, UDP_PORT))

        while True:
            data, addr = sock.recvfrom(1024)  # buffer size is 1024 bytes
            s = data.decode()
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
        try:
            csv_arr = []
            for k,v in scores.items():
                row = ['Erg ID']
                row += ['Time', 'Distance', 'Avg Split']*len(v)
                csv_arr.append(row)

            counter = 1
            for k,v in scores.items():
                counter += 1
                name = getattr(self.monitor, 'erg'+str(k)).lname.text
                if name != '':
                    row = [name]
                else:
                    row = [k]
                for a,b,c in v:
                    row += [a,b,c]
                csv_arr.append(row)

            if len(scores.items()) == 0:
                print('No scores to upload')
                return

            filename = './workout_data/'+str(datetime.datetime.now())+' erg_data.csv'
            np.savetxt(filename, csv_arr, delimiter=',', fmt='%s')

            file1 = drive.CreateFile()
            file1.SetContentFile(filename)
            # {'convert': True} triggers conversion to a Google Drive document.
            file1.Upload({'convert': True})
            permission = file1.InsertPermission({
                'type': 'anyone',
                'value': 'anyone',
                'role': 'reader'})

            print(file1['alternateLink'])
            webbrowser.open(file1['alternateLink'])

            print('Uploaded')
        except:
            print('Error During Upload')

    def relogin(self):
        os.remove('credentials.json')

    def build(self):
        Window.minimum_height = 600
        Window.minimum_width = 800
        #Window.borderless = 1
        sm = ScreenManager(transition=NoTransition())
        self.graph = GraphScreen(name='graph')
        self.settings = Settings(name='settings')
        self.monitor = ErgMonitorBase(name='monitor')
        self.scores = WorkoutScores(name='scores')
        #self.graph.update_graphs()
        Clock.schedule_interval(self.graph.update_graphs, 1 / 60.)


        self.start_update_thread()


        sm.add_widget(self.monitor)
        sm.add_widget(self.scores)
        sm.add_widget(self.settings)
        sm.add_widget(self.graph)

        return sm

    def cleanup(self):
        self.p.kill()




if __name__ == '__main__':

    app = ErgMonitorApp()
    atexit.register(app.cleanup)
    app.run()

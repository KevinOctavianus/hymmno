# -*- coding: utf-8 -*-

import os
import csv
import random
import StringIO
from operator import itemgetter
from operator import attrgetter
import httplib2
from lxml import etree
import hy_data

lexicon_data = hy_data.LoadFromTextFile()[1]
dialect = {"Central": 1, "Cult Ciel": 2, "Cluster": 3, "Ancient Metafalss": 5,
           "Pastalia": 6, "Alpha (Eolia)": 7, "": 50}

def lexicon_to_csv():
    fo = open("hymmnos.csv", "w")
    fo.write("Hymmnos,POS,Meaning-jp,Meaning-en,Dialect\r\n")

    for line in lexicon_data:
        line = map(lambda x: x.replace('"', '""').strip(), line)
        s = '"%s"\n' % ('","'.join(line))
        fo.write(s.encode('utf-8'))
    
    fo.close()

def get_hymmnos_server_pos():
    h = httplib2.Http("")

    #fo = open("hymmnos_server_pos", "w")
    for p in 'abcdefghijklmnopqrstuvwxyz0':
        resp, content = h.request("http://hymmnoserver.uguu.ca/browse.php?page=%s" % (p))
        print p
    
        page = etree.HTML(content)
        hrefs = page.xpath("//a")
        for href in hrefs:
            s = href.values()[0]
            spos = s.find("popUpWord('")
            epos = s.find(")")
            if spos != -1:
                spos += 10
                line = map(lambda x: x.strip('"\' '), s[spos: epos].split(","))
                fo.write("%s\n" % (",".join(line)))
            
    fo.close()
    print "END"
    
class HymmnoServer:
    def __init__(self):
        pass
    
    def Request(self, url):
        h = httplib2.Http("")
        resp, content = h.request(url)
        
        content = content.replace("<br/>", "")
        self.content = content
        parser = etree.HTMLParser(encoding='utf-8')
        self.page = etree.HTML(content)
    
    def get_en_meaning(self):
        f = self.page.xpath("/html/body/table[1]/tr[2]/td/span")
        return f[0].text[:f[0].text.find("[")]
    
    def get_jp_meaning(self):
        f = self.page.xpath("/html/body/table[1]/tr[2]/td/span")
        return f[0].text[f[0].text.find("]") + 1: f[0].text.rfind("[")]
            
    def get_phonetic(self):    
        f = self.page.xpath("/html/body/table[1]/tr[2]/td/span")
        return f[0].text[f[0].text.find("["): f[0].text.find("]") + 1]

    def get_dialect(self):
        f = self.page.xpath("//span")
        return f[3].text

    def get_POS(self):
        f = self.page.xpath("//span")
        return f[4].text
    
    def get_related(self):
        pass

class Hymmnos():
    def __init__(self):
        self._csvfile = {}
        self._label = []
    
    def _csv_strip(self, value):
        value = value.strip('"').replace('"', '""')
        value = csv.reader(StringIO.StringIO(value)).next()
        label = self.GetLabel()
        
        return {label[i]: v for i, v in enumerate(value)}
    
    def AddWord(self, word, value=None):
        if word not in self._csvfile:
            label = self.GetLabel()
            self._csvfile[word] = {key: "" for key in label}
            if value:
                if isinstance(value, str):
                    # By current label order, empty place still need comma
                    value = self._csv_strip(value)
                    self._csvfile[word] = value
                elif isinstance(value, dict):
                    for key, val in value.items():
                        self._csvfile[word][key] = val
                    
    def AppendLabel(self, label, pos=None, updateAll=False):
        if label not in self._label:
            if pos:
                self._label = self._label[:pos] + [label] + self._label[pos:]
            else:
                self._label.append(label)
            if updateAll:
                for item in self._csvfile:
                    self._csvfile[item][label] = ""
                    
    def UpdateWord(self, word, value=None):
        pass
    
    def DelWord(self, word):
        self._csvfile.pop(word)
                        
    def GetLabel(self):
        return list(self._label)
    
    def GetLexicon(self):
        return self._csvfile
    
    def read_csv(self, path):
        csvfile = csv.reader(open(path, "r"))
        self.SetLabel(csvfile.next())
        
        self._csvfile = {}
        for line in csvfile:
            self._csvfile[line[0]] = {key: line[i] for i, key in enumerate(self._label)}
            
    def SaveCsv(self, path):
        fo = open(path, "w")
        fo.write("%s\n" % (",".join(self.GetLabel())))
        
        for hym in sorted(self._csvfile.keys()):
            data = [self._csvfile[hym][label] for label in self._label]
            data = map(lambda x: isinstance(x, str) and x.replace('"', '""').decode('utf-8', 'ignore') or x, data)
            s = '"%s"\n' % ('","'.join(data))
            fo.write(s.encode('utf-8'))
            
        fo.close()
            
            
    def SetLabel(self, value):
        self._label = value
        
def update_lxeicon():
    hymm_pos = map(lambda x: x.strip("\n").split(","), open("hymmnos_server_pos", "r").readlines())
    hymm_pos = {i[0]: i[1] for i in hymm_pos}
    hymm_dict = Hymmnos()
    hymm_dict.read_csv("hymmnos.csv")
    lexicon = hymm_dict.GetLexicon()
    blacklist = ['ChronicleKey', 'rhaplanca', 'Viena', 'Harmonious', ]
    url = "http://hymmnoserver.uguu.ca/word.php?word=%s&dialect=%s"

    hymm_dict.AppendLabel("Phonetic", pos=2, updateAll=True)

    for hym, dia in hymm_pos.items():
        gett = HymmnoServer()
        gett.Request(url % (hym, dia))
        phonetic = gett.get_phonetic()
    
        print hym, phonetic, "in current dict: %s" % (hym in lexicon)
        
        if hym in lexicon:
            lexicon[hym]['Phonetic'] = phonetic
            lexicon[hym]['Dialect'] = gett.get_dialect()
        elif hym not in blacklist:
            hymm_dict.AddWord(hym)
            lexicon[hym]['Hymmnos'] = hym
            lexicon[hym]['POS'] = gett.get_POS()
            lexicon[hym]['Phonetic'] = phonetic
            lexicon[hym]['Meaning-en'] = gett.get_en_meaning()
            lexicon[hym]['Meaning-jp'] = gett.get_jp_meaning()
            lexicon[hym]['Dialect'] = gett.get_dialect()
    
    hymm_dict.SaveCsv("hymm_test.csv")
    print "END"
    
def tomobi_1():
    hymm_dict = Hymmnos()
    hymm_dict.read_csv("hymm_test.csv")
    hymm_dict.SetLabel(['Hymmnos', 'Phonetic', 'POS', 'Meaning-jp', 'Meaning-en', 'Dialect'])
    lexicon = hymm_dict.GetLexicon()
    label = hymm_dict.GetLabel()
    
    fo = open("HymmnoLexicon", "w")
    for hym in sorted(lexicon.keys()):
        fo.write("%s\t" % (hym))
        data = [lexicon[hym][key] for key in label[1:]]
        fo.write("\\n".join(data) + "\n")
        
    fo.close()

def tomobi_2():
    hymm_dict = Hymmnos()
    hymm_dict.read_csv("hymm_test.csv")
    hymm_dict.SetLabel(['Hymmnos', 'Phonetic', 'POS', 'Meaning-en', 'Dialect'])
    lexicon = hymm_dict.GetLexicon()
    label = hymm_dict.GetLabel()
    
    fo = open("HymmnoLexicon.tab", "w")
    for hym in sorted(lexicon.keys()):
        fo.write("%s\t" % (hym))
        paragraph = "%s\\n" \
                    "▪<i><font face='mono'>%s</font></i>\\n" \
                    "%s\\n" \
                    "\\n<b>&lt;DIALECT&gt;</b> %s\\n" % (
            lexicon[hym]["Phonetic"],
            lexicon[hym]["POS"], lexicon[hym]["Meaning-en"],
            lexicon[hym]["Dialect"]
            )
        fo.write(paragraph + "\n")
    fo.close()
    os.system("python2 tab2opf.py -utf HymmnoLexicon.tab")
    #os.system("wine mobigen HymmnoLexicon.tab")

class HymmnosLyric():
    def __init__(self):
        self.lyric = {}
    
    def Read(self, path):
        fi = open(path, "r")
        
        data = []
        for line in fi.readlines():
            if line.startswith("---"):
                self.lyric[line.strip("\r\n-")] = data
                data = []
            else:
                data.append(line.strip("\n").split())
    
    def GetAlbum(self, song):
        """
        return the album
        """
        pass
    
    def GetLyric(self, song):
        """
        return the lyric of song
        """
        pass
    
    def GetWordPos(self, word, randomize=False, song=None):
        result = []
        if not song:
            items = self.lyric.items()
            if randomize:
                random.shuffle(items)

            for song_name, lyr in items:
                for row_num, row in enumerate(lyr):
                    if word in row:
                        result.append((song_name, (row_num, row.index(word))))
        else:
            for row_num, row in enumerate(self.lyric[song]):
                if word in row:
                    result.append((song, (row_num, row.index(word))))
    
        return result
    
    def GetPosLyric(self, song, row):
        """
        return lyric by row, col
        """
        
        return " ".join(self.lyric[song][row])
    
def HymmnosLyricTDD():
    s = HymmnosLyric()
    s.Read("wordlist")
    print s.lyric['Singing Hill']
    print s.GetWordPos("Wee", "Singing Hill")
    print s.GetPosLyric("Singing Hill", 10)
    
def tomobi_3():
    hymm_dict = Hymmnos()
    hymm_dict.read_csv("hymm_test.csv")
    hymm_dict.SetLabel(['Hymmnos', 'Phonetic', 'POS', 'Meaning-en', 'Dialect'])
    lexicon = hymm_dict.GetLexicon()
    label = hymm_dict.GetLabel()
    
    hymm_lyr = HymmnosLyric()
    hymm_lyr.Read("wordlist")
    
    fo = open("HymmnoLexicon.tab", "w")
    for hym in sorted(lexicon.keys()):
        fo.write("%s\t" % (hym))
        usage = hymm_lyr.GetWordPos(hym, randomize=True)
        if usage:
            usage = "%s&nbsp;&nbsp;—<font size='1'>%s</font>" % (
                hymm_lyr.GetPosLyric(usage[0][0], usage[0][1][0]),
                usage[0][0]
                )
        
        paragraph = "%s\\n" \
                    "▪<i><font face='mono'>%s</font></i>\\n" \
                    "%s" % (
            lexicon[hym]["Phonetic"],
            lexicon[hym]["POS"],
            lexicon[hym]["Meaning-en"],
            )
        
        if usage:
            paragraph += ": <i><font color='#404040'>%s</font></i>\\n" % (usage)
        else:
            paragraph += "\\n"
        
        paragraph += "\\n<b>&lt;DIALECT&gt;</b> %s\\n" % (lexicon[hym]["Dialect"])
        
        fo.write(paragraph + "\n")
    fo.close()
    os.system("python2 tab2opf.py -utf HymmnoLexicon.tab")
    #os.system("wine mobigen HymmnoLexicon.tab")
    
tomobi_3()
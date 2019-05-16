import requests
from lxml import html
import json
import io
import sqlite3
import time
from datetime import datetime
import os
from apscheduler.schedulers.blocking import BlockingScheduler


def tick():
    print('Tick! The time is: %s' % datetime.now())




        #print(film_json['resource_content'])
    #fp.close()

class Movie():
    def __init__(self):
        self.nameEn = ''
        self.nameCn = ''
        self.url = ''
        self.rid = ''
        self.sidetabs = []

    def toTuble(self):
        return (self.nameEn,self.nameCn,self.url,self.rid)

class Zmz:
    def __init__(self):
        self.account = ''  # 账号
        self.password = '' # 密码
        self.session = requests.session()
        self.domain_url = 'http://www.zmz2019.com'
        self.sql = 'INSERT INTO movies (namecn, nameen, season, episode, magnet, thunder, resolution, flag) VALUES (?,?,?,?,?,?,?,?);'
        self.favMovies = []
        self.resolution = ''
        self.unDown = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.0.1 Safari/605.1.15'
        }

    def getFav(self):
        fav_page = self.session.get('http://www.zmz2019.com/user/fav',headers=self.headers)
        tree = html.fromstring(fav_page.text)
        films = tree.xpath('/html/body/div[2]/div/div/div[2]/div/ul/li')
        self.favMovie = []
        for film in films:
            movie = Movie()
            film_name_en = film.xpath('./div[2]/p[1]/text()')
            film_name_cn = film.xpath('./div[2]/div[1]/strong/a/text()')
            movie.nameEn = ''.join(film_name_en)
            movie.nameCn = ''.join(film_name_cn)
            film_url = film.xpath('./div[2]/div[1]/strong/a/@href')
            film_url =  ''.join(film_url)
            rid = film_url.split('/')
            movie.rid = rid[len(rid) - 1]
            movie.url = self.domain_url + '/resource/index_json/rid/' + movie.rid + '/channel/tv'
            self.favMovies.append(movie)
        #print(self.favMovies)


    def loginZmz(self):
        payload = {'account': self.account, 'password': self.password, 'remember': '2',
                   'url_back': 'http%3A%2F%2Fwww.zmz2019.com%2F'}
        r = self.session.post('http://www.zmz2019.com/User/Login/ajaxLogin', payload,headers=self.headers)
        #print(r.text)
        c = requests.cookies.RequestsCookieJar()  # 利用RequestsCookieJar获取
        self.session.cookies.update(c)
        resp_json = json.loads(r.text)
        return resp_json['status']

    def getFilm(self,movie):
        movieList = []
        print(movie.nameCn)
        film_page = self.session.get(movie.url,headers=self.headers)
        pos = film_page.text.find('{')
        film_info = film_page.text[pos:]
        film_json = json.loads(film_info)
        real_url = film_json['resource_content']
        tree = html.fromstring(str(real_url))
        # print(real_url)
        real_url = tree.xpath('//div[1]/div[1]/h3[1]/a/@href')
        real_url = ''.join(real_url)
        real_page = self.session.get(real_url,headers=self.headers)
        tree = html.fromstring(real_page.text)
        sidetabs = tree.xpath('//*[@id="menu"]/li')
        for sidetab in sidetabs:
            sideid = ''.join(sidetab.xpath('./a/@href'))
            sidename = ''.join(sidetab.xpath('./a/text()'))
            print(sidename)
            res = sidetab.xpath('//*[@id=\"' + sideid[1:] + '\"]/ul/li')
            # 解析不同的季
            for re in res:
                down_name = re.xpath('./a/text()')
                down_name = ''.join(down_name)
                hrefs = re.xpath('./a/@href')
                hrefs = ''.join(hrefs)[1:]
                if 'APP' in hrefs:
                    continue
                print( hrefs)
                # fp.write('1333:' + hrefs[1:] + '\n')
                down_urls = tree.xpath('//*[@id=\"' + hrefs + '\"]/ul/li')
                # 解析同一季不同分辨率
                for li in down_urls:
                    film_name = ''.join(li.xpath('./div/span[1]/text()'))
                    # fp.write(film_name + '\n')
                    season = ''
                    episode = ''
                    film_name = film_name.split(' ')
                    if len(film_name) >= 2:
                        season = film_name[0]
                        episode = film_name[1]
                    # print(film_name)

                    # 解析不同的集
                    magnet = ''
                    thunder = ''
                    for links in li.xpath('./ul/li'):
                        down_type = ''.join(links.xpath('./a/p/text()'))
                        film_downurl = ''.join(links.xpath('./a/@href'))
                        # print(down_type +":"+ film_downurl)

                        if '迅雷' in down_type:
                            thunder = film_downurl
                        elif '磁力' in down_type:
                            magnet = film_downurl
                            # fp.write(down_type +":"+ film_downurl + '\n')
                    hrefs = hrefs.split('-')
                    if len(hrefs) >=1:
                        hrefs = hrefs[len(hrefs)-1]
                    tmp_data = (movie.nameCn, movie.nameEn, season, episode, magnet, thunder, hrefs, 0)
                    movieList.append(tmp_data)

        try:
            conn = sqlite3.connect('zmz.db')
            cur = conn.cursor()
            cur.executemany(self.sql, movieList)
            conn.commit()
        except (sqlite3.OperationalError, sqlite3.IntegrityError) as e:
            print('插入movies失败:' + '\t' + e.args[0])
        finally:
            conn.close()

    def selectUndown(self):
        try:
            sql = 'select magnet from movies where resolution = ? and flag = ?;'
            conn = sqlite3.connect('zmz.db')
            cur = conn.cursor()
            cursor = cur.execute(sql, (self.resolution,0,))
            for row in cursor:
                self.unDown.append(row[0])
        finally:
            conn.close()

    def updateFlag(self,magnet):
        try:
            sql = 'update movies set flag = ? where magnet = ?;'
            conn = sqlite3.connect('zmz.db')
            conn.execute(sql, (1,magnet,))
            conn.commit()
        finally:
            conn.close()

class Nas:
    def __init__(self):
        self.account = ''  # 账号
        self.passwd = '' # 密码
        self.url = '' # 地址
        self.session = requests.session()
        self.DownloadStationTask = ''
        self.AuthUrl = ''
        self.sid = ''
        self.taskerrorList = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.0.1 Safari/605.1.15'
        }

    def getPath(self):
        if 'https' in self.url:
            resp_data = self.session.get(self.url + '/webapi/query.cgi?api=SYNO.API.Info&version=1&method=query&query=SYNO.API.Auth,SYNO.DownloadStation.Task',verify=False,headers=self.headers)
        else:
            resp_data = self.session.get(self.url + '/webapi/query.cgi?api=SYNO.API.Info&version=1&method=query&query=SYNO.API.Auth,SYNO.DownloadStation.Task',headers=self.headers)
        #print(resp_data.text)
        resp_json = json.loads(resp_data.text)
        self.DownloadStationTask = '/webapi/' + str( resp_json['data']['SYNO.DownloadStation.Task']['path'] )
        self.AuthUrl = '/webapi/' + str( resp_json['data']['SYNO.API.Auth']['path'] )
        #print(self.DownloadStationTask)
        #print(self.AuthUrl)

    def loginDS(self):
        if 'https' in self.url:
            resp_data = self.session.get(self.url + self.AuthUrl + '?api=SYNO.API.Auth&version=2&method=login&account=' + self.account + '&passwd=' + self.passwd + '&session=DownloadStation&format=cookie',verify=False,headers=self.headers)
        else:
            resp_data = self.session.get(self.url + self.AuthUrl + '?api=SYNO.API.Auth&version=2&method=login&account=' + self.account + '&passwd=' + self.passwd + '&session=DownloadStation&format=cookie',headers=self.headers)

        resp_json = json.loads(resp_data.text)
        self.sid = str( resp_json['data']['sid'])

    def queryTask(self):
        if 'https' in self.url:
            resp_data = self.session.get(self.url + self.DownloadStationTask + '?api=SYNO.DownloadStation.Task&version=1&method=list',verify=False,headers=self.headers)
        else:
            resp_data = self.session.get(self.url + self.DownloadStationTask + '?api=SYNO.DownloadStation.Task&version=1&method=list',headers=self.headers)
        #print(resp_data.text)
        resp_json = json.loads(resp_data.text)
        tasks = resp_json['data']['tasks']
        for task in tasks:
            id = task['id']
            status = task['status']
            print( str(id) +'\t' + str(status))
            if 'error' in str(status):
                self.taskerrorList.append(str(id))
            elif 'finished' in str(status):
                self.taskerrorList.append(str(id))

        print(self.taskerrorList)

    def putTask(self, downloadUrl ):
        downuri = {'api': 'SYNO.DownloadStation.Task', 'version': '1', 'method': 'create','uri': str(downloadUrl)}
        if 'https' in self.url:
            resp_data = self.session.post(self.url + self.DownloadStationTask, downuri, verify=False,headers=self.headers )
        else:
            resp_data = self.session.post(self.url + self.DownloadStationTask, downuri,headers=self.headers)
        #print(resp_data.text)
        resp_json = json.loads(resp_data.text)
        return resp_json['success']

    def deleteTask(self, id):
        if 'https' in self.url:
            resp_data = self.session.get(self.url + self.DownloadStationTask + '?api=SYNO.DownloadStation.Task&version=1&method=delete&id='+ str(id) + '&force_complete=false', verify=False,headers=self.headers )
        else:
            resp_data = self.session.get(self.url + self.DownloadStationTask + '?api=SYNO.DownloadStation.Task&version=1&method=delete&id='+ str(id) + '&force_complete=false',headers=self.headers)
        resp_json = json.loads(resp_data.text)
        return resp_json['success']

    def deleteAllErrorTask(self):
        for id in self.taskerrorList:
            self.deleteTask(id)
        return

def getZMZ():
    zmz = Zmz()
    nas = Nas()

    with open("zmz.json", 'r') as f:
        temp = json.loads(f.read())
        zmz.account = temp['zmz']['account']
        zmz.password = temp['zmz']['password']
        zmz.resolution = temp['zmz']['resolution']
        nas.url = temp['nas']['url']
        nas.account = temp['nas']['account']
        nas.passwd = temp['nas']['passwd']

    zmz.loginZmz()
    zmz.getFav()
    for movie in zmz.favMovies:
        zmz.getFilm(movie)
    zmz.selectUndown()

    if len(zmz.unDown) >= 1:
        nas.getPath()
        nas.loginDS()
        for magnet in zmz.unDown:
            flag = nas.putTask(str(magnet))
            if flag:
                zmz.updateFlag(str(magnet))
        time.sleep(2)
        nas.queryTask()
        nas.deleteAllErrorTask()



if __name__=='__main__':

    scheduler = BlockingScheduler()
    scheduler.add_job(getZMZ, 'interval', hours=1)
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C    '))

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass




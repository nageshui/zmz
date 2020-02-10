# -*- coding: utf-8 -*-
import requests
from lxml import html
import json
import io
import sqlite3
import time
from datetime import datetime
import os
# from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
import argparse
import urllib.parse


def getpath():
    return os.path.split(os.path.realpath(__file__))[0]


class Movie():
    def __init__(self):
        self.nameEn = ''
        self.nameCn = ''
        self.url = ''
        self.rid = ''
        self.sidetabs = []
        self.isMoive = False

    def toTuble(self):
        return (self.nameEn, self.nameCn, self.url, self.rid, self.isMoive)


class Zmz:
    def __init__(self):
        self.account = ''  # 账号
        self.password = ''  # 密码
        self.session = requests.session()
        self.domain_url = 'http://www.rrys2019.com'
        self.sql = 'INSERT INTO movies (namecn, nameen, season, episode, magnet, thunder, resolution, flag) VALUES (?,?,?,?,?,?,?,?);'
        self.favMovies = []
        self.resolution = ''
        self.unDown = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.0.1 Safari/605.1.15'
        }
        self.dbpath = getpath() + '/zmz.db'

    def getFav(self, page):
        try:
            fav_page = self.session.get('http://www.rrys2019.com/user/fav' + str(page), headers=self.headers)
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
                film_url = ''.join(film_url)
                rid = film_url.split('/')
                movie.rid = rid[- 1]
                if '电影' in movie.nameCn:
                    movie.url = self.domain_url + '/resource/index_json/rid/' + movie.rid + '/channel/movie'
                    movie.isMoive = True
                else:
                    movie.url = self.domain_url + '/resource/index_json/rid/' + movie.rid + '/channel/tv'
                    movie.isMoive = False

                self.favMovies.append(movie)

            pages = tree.xpath('//div[@class="pages"]/div/a')
            for tmp in pages:
                nextpage = ''.join(tmp.xpath('./text()'))
                # print(nextpage)
                if '下一页' in nextpage:
                    nextpage = ''.join(tmp.xpath('./@href'))
                    self.getFav(nextpage)

        except Exception as e:
            print(e.args[0]);

    def loginZmz(self):
        payload = {'account': self.account, 'password': self.password, 'remember': '2',
                   'url_back': 'http%3A%2F%2Fwww.rrys2019.com%2F'}
        r = self.session.post('http://www.rrys2019.com/User/Login/ajaxLogin', payload, headers=self.headers)
        c = requests.cookies.RequestsCookieJar()  # 利用RequestsCookieJar获取
        self.session.cookies.update(c)
        resp_json = json.loads(r.text)
        return resp_json['status']

    def getFilmByJson(self, movie):
        try:
            isMoive = False
            print(movie.toTuble())
            film_page = self.session.get(movie.url, headers=self.headers)
            pos = film_page.text.find('{')
            film_info = film_page.text[pos:]
            film_json = json.loads(film_info)
            real_url = film_json['resource_content']
            if len(real_url) <= 0:
                return
            tree = html.fromstring(str(real_url))
            real_url = tree.xpath('//div[1]/div[1]/h3[1]/a/@href')
            if len(real_url) <= 0:
                return
            real_url = ''.join(real_url).split('?')
            ym = urllib.parse.urlparse(real_url[0]).hostname
            scheme = urllib.parse.urlparse(real_url[0]).scheme

            print(scheme + '://' + ym + '/api/v1/static/resource/detail?' + real_url[1])
            real_page = self.session.get(scheme + '://' + ym + '/api/v1/static/resource/detail?' + real_url[1],
                                         headers=self.headers)

            # print(str(real_page.text))
            film_json = json.loads(str(real_page.text))
            nameCn = film_json['data']['info']['cnname']
            nameEn = film_json['data']['info']['enname']

            # print(film_json['data']['list'])
            for season in film_json['data']['list']:
                seasonname = season['season_cn']
                # print(seasonname)
                if '周边资源' in seasonname:
                    continue
                # 解析不同的分辨率
                for item, itemvalue in season['items'].items():
                    # print(item)
                    if 'APP' in item:
                        continue

                    if isinstance(itemvalue, list):
                        for detail in itemvalue:
                            episode = detail['episode']
                            # print(episode)
                            if detail['files'] == None:
                                print('is None')
                                continue
                            # print(detail['files'])
                            for way in detail['files']:
                                magnet = ''
                                thunder = ''
                                if 'thunder' in way['address']:
                                    thunder = way['address']
                                elif 'magnet' in way['address']:
                                    magnet = way['address']

                                if len(magnet) <= 0 and len(thunder) <= 0:
                                    continue
                                tmp_data = (nameCn, nameEn, seasonname, episode, magnet, thunder, item, 0)
                                self.insertMoive(tmp_data)

        except Exception as e:
            print(e.args[0]);

    def insertMoive(self, movieData):
        try:
            conn = sqlite3.connect(self.dbpath)
            cur = conn.cursor()
            cur.execute(self.sql, movieData)
            conn.commit()
            print('保存' + '\t' + str(movieData))
        except (sqlite3.OperationalError, sqlite3.IntegrityError) as e:
            print('插入movies失败:' + '\t' + e.args[0])
        finally:
            conn.close()

    def getFilm(self, movie):
        isMoive = False
        movieList = []
        print(movie.toTuble())
        film_page = self.session.get(movie.url, headers=self.headers)
        pos = film_page.text.find('{')
        film_info = film_page.text[pos:]
        film_json = json.loads(film_info)
        real_url = film_json['resource_content']

        tree = html.fromstring(str(real_url))
        real_url = tree.xpath('//div[1]/div[1]/h3[1]/a/@href')
        real_url = ''.join(real_url)
        real_page = self.session.get(real_url, headers=self.headers)
        tree = html.fromstring(real_page.text)

        if movie.isMoive:
            sidetabs = tree.xpath('//*[@id="scrollspy"]/ul/li')
        else:
            sidetabs = tree.xpath('//*[@id="menu"]/li')
        """
        sidetabs = tree.xpath('//*[@id="menu"]/li')

        # 电影的sidetab和电视剧不同
        if len(sidetabs) == 0:
            isMoive = True
            sidetabs = tree.xpath('//*[@id="scrollspy"]/ul/li')
        """

        for sidetab in sidetabs:
            sideid = ''.join(sidetab.xpath('./a/@href'))
            sidename = ''.join(sidetab.xpath('./a/text()'))
            res = sidetab.xpath('//*[@id=\"' + sideid[1:] + '\"]/ul/li')
            # 解析不同的季
            for re in res:
                down_name = re.xpath('./a/text()')
                down_name = ''.join(down_name)
                hrefs = re.xpath('./a/@href')
                hrefs = ''.join(hrefs)[1:]
                if 'APP' in hrefs:
                    continue
                elif '预告片' in hrefs:
                    continue
                elif '游戏' in hrefs:
                    continue

                down_urls = tree.xpath('//*[@id=\"' + hrefs + '\"]/ul/li')
                # 解析同一季不同分辨率
                for li in down_urls:
                    film_name = ''.join(li.xpath('./div/span[1]/text()'))
                    season = ''
                    episode = ''
                    film_name = film_name.split(' ')
                    if len(film_name) >= 2:
                        season = film_name[0]
                        episode = film_name[1]

                    # 解析不同的集
                    magnet = ''
                    thunder = ''
                    for links in li.xpath('./ul/li'):
                        down_type = ''.join(links.xpath('./a/p/text()'))
                        film_downurl = ''.join(links.xpath('./a/@href'))

                        if 'thunder' in film_downurl:
                            thunder = film_downurl
                        elif 'magnet' in film_downurl:
                            magnet = film_downurl
                    hrefs = hrefs.split('-')
                    if len(hrefs) >= 1:
                        hrefs = hrefs[-1]
                    tmp_data = (movie.nameCn, movie.nameEn, season, episode, magnet, thunder, hrefs, 0)
                    movieList.append(tmp_data)

        try:
            print(movieList)
            conn = sqlite3.connect(self.dbpath)
            cur = conn.cursor()
            cur.executemany(self.sql, movieList)
            conn.commit()
            print('保存' + '\t' + movie.nameCn)
        except (sqlite3.OperationalError, sqlite3.IntegrityError) as e:
            print('插入movies失败:' + '\t' + e.args[0])
        finally:
            conn.close()

    def selectUndown(self):
        nameenList = []
        self.unDown = []
        try:
            conn = sqlite3.connect(self.dbpath)
            cur = conn.cursor()

            sql = 'SELECT DISTINCT nameen,season,episode FROM movies WHERE flag = ? ORDER BY nameen,season,episode DESC'
            name_cur = cur.execute(sql, (0,))
            for nameen in name_cur:
                nameenList.append((nameen[0], nameen[1], nameen[2]))

            # 查找未下载的magnet
            for film in nameenList:
                print(film)
                # 根据分辨率优先级查找 如优先级高的分辨率找不到 查找备用分辨率片源
                for resolution in self.resolution:
                    print('查询分辨率' + '\t' + resolution)
                    sql = 'SELECT magnet,flag FROM movies WHERE nameen= ? AND season =? AND episode=? AND length(magnet) > 1 AND resolution =?'
                    name_cur = cur.execute(sql, (film[0], film[1], film[2], resolution,))
                    row = name_cur.fetchone()
                    if row is None:
                        print('未查询到分辨率' + '\t' + resolution)
                    else:
                        if row[1] == 0:
                            self.unDown.append(row[0])
                        break
        finally:
            conn.close()

    def updateFlag(self, magnet):
        try:
            sql = 'update movies set flag = ? where magnet = ?;'
            conn = sqlite3.connect(self.dbpath)
            conn.execute(sql, (1, magnet,))
            conn.commit()
        finally:
            conn.close()

    def first(self):
        try:
            sql = 'update movies set flag = ?;'
            conn = sqlite3.connect(self.dbpath)
            conn.execute(sql, (1,))
            conn.commit()
        finally:
            conn.close()


class Nas:
    def __init__(self):
        self.account = ''  # 账号
        self.passwd = ''  # 密码
        self.url = ''  # 地址
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
            resp_data = self.session.get(
                self.url + '/webapi/query.cgi?api=SYNO.API.Info&version=1&method=query&query=SYNO.API.Auth,SYNO.DownloadStation.Task',
                verify=False, headers=self.headers)
        else:
            resp_data = self.session.get(
                self.url + '/webapi/query.cgi?api=SYNO.API.Info&version=1&method=query&query=SYNO.API.Auth,SYNO.DownloadStation.Task',
                headers=self.headers)
        resp_json = json.loads(resp_data.text)
        self.DownloadStationTask = '/webapi/' + str(resp_json['data']['SYNO.DownloadStation.Task']['path'])
        self.AuthUrl = '/webapi/' + str(resp_json['data']['SYNO.API.Auth']['path'])

    def loginDS(self):
        if 'https' in self.url:
            resp_data = self.session.get(
                self.url + self.AuthUrl + '?api=SYNO.API.Auth&version=2&method=login&account=' + self.account + '&passwd=' + self.passwd + '&session=DownloadStation&format=cookie',
                verify=False, headers=self.headers)
        else:
            resp_data = self.session.get(
                self.url + self.AuthUrl + '?api=SYNO.API.Auth&version=2&method=login&account=' + self.account + '&passwd=' + self.passwd + '&session=DownloadStation&format=cookie',
                headers=self.headers)

        resp_json = json.loads(resp_data.text)
        self.sid = str(resp_json['data']['sid'])

    def queryTask(self):
        if 'https' in self.url:
            resp_data = self.session.get(
                self.url + self.DownloadStationTask + '?api=SYNO.DownloadStation.Task&version=1&method=list',
                verify=False, headers=self.headers)
        else:
            resp_data = self.session.get(
                self.url + self.DownloadStationTask + '?api=SYNO.DownloadStation.Task&version=1&method=list',
                headers=self.headers)
        resp_json = json.loads(resp_data.text)
        tasks = resp_json['data']['tasks']
        for task in tasks:
            id = task['id']
            status = task['status']
            print(str(id) + '\t' + str(status))
            if 'error' in str(status):
                self.taskerrorList.append(str(id))
            elif 'finished' in str(status):
                self.taskerrorList.append(str(id))

    def putTask(self, downloadUrl):
        downForm = {'api': 'SYNO.DownloadStation.Task', 'version': '1', 'method': 'create', 'uri': str(downloadUrl)}
        if 'https' in self.url:
            resp_data = self.session.post(self.url + self.DownloadStationTask, downForm, verify=False,
                                          headers=self.headers)
        else:
            resp_data = self.session.post(self.url + self.DownloadStationTask, downForm, headers=self.headers)
        resp_json = json.loads(resp_data.text)
        return resp_json['success']

    def deleteTask(self, id):
        if 'https' in self.url:
            resp_data = self.session.get(
                self.url + self.DownloadStationTask + '?api=SYNO.DownloadStation.Task&version=1&method=delete&id=' + str(
                    id) + '&force_complete=false', verify=False, headers=self.headers)
        else:
            resp_data = self.session.get(
                self.url + self.DownloadStationTask + '?api=SYNO.DownloadStation.Task&version=1&method=delete&id=' + str(
                    id) + '&force_complete=false', headers=self.headers)
        resp_json = json.loads(resp_data.text)
        return resp_json['success']

    def deleteAllErrorTask(self):
        for id in self.taskerrorList:
            self.deleteTask(id)
        return


def getZMZ():
    zmz = Zmz()
    nas = Nas()

    with open(getpath() + "/zmz.json", 'r') as f:
        temp = json.loads(f.read())
        zmz.account = temp['zmz']['account']
        zmz.password = temp['zmz']['password']
        zmz.resolution = str(temp['zmz']['resolution']).split(',')
        nas.url = temp['nas']['url']
        nas.account = temp['nas']['account']
        nas.passwd = temp['nas']['passwd']

    zmz.loginZmz()
    zmz.getFav('')
    for movie in zmz.favMovies:
        zmz.getFilmByJson(movie)

    if args.init == 1:
        zmz.first()

    zmz.selectUndown()
    nas.getPath()
    nas.loginDS()
    print(zmz.unDown)
    if len(zmz.unDown) >= 1:
        for magnet in zmz.unDown:
            flag = nas.putTask(str(magnet))
            if flag:
                zmz.updateFlag(str(magnet))
    time.sleep(2)
    nas.queryTask()
    nas.deleteAllErrorTask()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='manual to this script')
    parser.add_argument('--init', type=int, default=0)
    args = parser.parse_args()
    # print(args.init)
    getZMZ()
    """
    scheduler = BlockingScheduler()
    scheduler.add_job(getZMZ, 'interval', hours=1)
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C    '))

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
    """

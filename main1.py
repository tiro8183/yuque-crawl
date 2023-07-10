import sys
import requests
import json
import re
import os
import urllib.parse

# 定义一个用于下载语雀知识库的类
class YuqueBookDownloader:
    def __init__(self, url="https://www.yuque.com/burpheart/phpaudit"):
        self.url = url  # 知识库的URL
        self.table = str.maketrans('\/:*?"<>|' + "\n\r", "___________")  # 用于转换文件名的转换表
        self.list = {}  # 用于存储文档的信息
        self.temp = {}  # 用于存储临时信息
        self.summary = ""  # 用于存储知识库的目录

    # 获取知识库的信息并下载所有文档
    def get_book(self):
        try:
            response = requests.get(self.url)  # 发送GET请求获取知识库的页面
            response.raise_for_status()  # 如果响应状态码不是200，抛出异常
        except requests.exceptions.RequestException as e:
            print(f"Failed to get the book. Error: {e}")
            return

        # 从页面中提取知识库的信息
        data = re.findall(r"decodeURIComponent\(\"(.+)\"\)\);", response.content.decode('utf-8'))
        self.book_data = json.loads(urllib.parse.unquote(data[0]))  # 解码并解析知识库的信息

        # 如果知识库的下载目录不存在，创建该目录
        if not os.path.exists(f"download/{self.book_data['book']['id']}"):
            os.makedirs(f"download/{self.book_data['book']['id']}")

        # 处理知识库的目录中的每一项
        for doc in self.book_data['book']['toc']:
            self.process_doc(doc)

        # 写入知识库的目录
        self.write_summary()

    # 处理一项目录
    def process_doc(self, doc):
        if doc['type'] == 'TITLE':  # 如果这项是标题，处理标题
            self.process_title(doc)
        if doc['url'] != '':  # 如果这项有URL，处理URL
            self.process_url(doc)

    # 处理标题
    def process_title(self, doc):
        self.list[doc['uuid']] = {'0': doc['title'], '1': doc['parent_uuid']}  # 存储标题的信息
        self.temp[doc['uuid']] = self.get_temp(doc)  # 获取标题的临时信息
        # 如果标题对应的目录不存在，创建该目录
        if not os.path.exists(f"download/{self.book_data['book']['id']}/{self.temp[doc['uuid']]}"):
            os.makedirs(f"download/{self.book_data['book']['id']}/{self.temp[doc['uuid']]}")
        self.update_summary(doc)  # 更新知识库的目录

    # 处理URL
    def process_url(self, doc):
        if doc['parent_uuid'] != "":  # 如果这项有父标题，更新知识库的目录并下载文档
            self.update_summary_with_url(doc)
        else:  # 如果这项没有父标题，直接下载文档
            self.summary += " " + "* [" + doc['title'] + "](" + urllib.parse.quote(
                doc['title'].translate(self.table) + '.md') + ")" + "\n"
            self.save_page(doc['url'], f"download/{self.book_data['book']['id']}/{doc['title'].translate(self.table)}.md")

    # 获取标题的临时信息
    def get_temp(self, doc):
        uuid = doc['uuid']
        temp = ''
        while True:
            if self.list[uuid]['1'] != '':  # 如果这项有父标题，更新临时信息
                temp = self.update_temp(doc, uuid, temp)
                uuid = self.list[uuid]['1']
            else:  # 如果这项没有父标题，直接获取临时信息
                temp = self.update_temp(doc, uuid, temp)
                break
        return temp

    # 更新临时信息
    def update_temp(self, doc, uuid, temp):
        if temp == '':  # 如果临时信息为空，直接获取临时信息
            return doc['title'].translate(self.table)
        else:  # 如果临时信息不为空，更新临时信息
            return self.list[uuid]['0'].translate(self.table) + '/' + temp

    # 更新知识库的目录
    def update_summary(self, doc):
        if self.temp[doc['uuid']].endswith("/"):  # 如果临时信息以斜杠结尾，添加一级标题
            self.summary += "## " + self.temp[doc['uuid']][:-1] + "\n"
        else:  # 如果临时信息不以斜杠结尾，添加二级标题
            self.summary += "  " * (self.temp[doc['uuid']].count("/") - 1) + "* " + self.temp[doc['uuid']][
                                                                         self.temp[doc['uuid']].rfind("/") + 1:] + "\n"

    # 更新知识库的目录并下载文档
    def update_summary_with_url(self, doc):
        self.summary += "  " * self.temp[doc['parent_uuid']].count("/") + "* [" + doc['title'] + "](" + urllib.parse.quote(
            self.temp[doc['parent_uuid']] + "/" + doc['title'].translate(self.table) + '.md') + ")" + "\n"
        self.save_page(doc['url'],
                  f"download/{self.book_data['book']['id']}/{self.temp[doc['parent_uuid']]}/{doc['title'].translate(self.table)}.md")

    # 下载文档
    def save_page(self, slug, path):
        try:
            response = requests.get(
                f'https://www.yuque.com/api/docs/{slug}?book_id={self.book_data["book"]["id"]}&merge_dynamic_data=false&mode=markdown')  # 发送GET请求获取文档的页面
            response.raise_for_status()  # 如果响应状态码不是200，抛出异常
        except requests.exceptions.RequestException as e:
            print(f"Failed to download the document. The page might have been deleted. Error: {e}")
            return

        document_data = json.loads(response.content)  # 解析文档的信息

        try:
            with open(path, 'w', encoding='utf-8') as f:  # 打开文件准备写入
                f.write(document_data['data']['sourcecode'])  # 写入文档的内容
        except IOError as e:
            print(f"Failed to write the document to file. Error: {e}")

    # 写入知识库的目录
    def write_summary(self):
        try:
            with open(f"download/{self.book_data['book']['id']}/SUMMARY.md", 'w', encoding='utf-8') as f:  # 打开文件准备写入
                f.write(self.summary)  # 写入知识库的目录
        except IOError as e:
            print(f"Failed to write the summary to file. Error: {e}")


if __name__ == '__main__':
    downloader = YuqueBookDownloader()  # 创建一个下载器
    if len(sys.argv) > 1:  # 如果命令行参数有额外的URL，使用该URL
        downloader.url = sys.argv[1]
    downloader.get_book()  # 获取知识库并下载所有文档

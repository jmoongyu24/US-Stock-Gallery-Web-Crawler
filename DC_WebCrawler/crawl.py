from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

import os, time
from bs4 import BeautifulSoup
from time import sleep
import pandas as pd
from datetime import datetime
from multiprocessing import Pool, Manager

# Chrome 옵션 설정
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--log-level=3')
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

driver = webdriver.Chrome(options=chrome_options)

start_date = time.strptime("2025.11.13 00:00:00", "%Y.%m.%d %H:%M:%S")
end_date = time.strptime("2025.11.13 00:01:00", "%Y.%m.%d %H:%M:%S")

# 수집한 정보를 저장하는 리스트
writer_list = [] # 작성자 아이디
title_list = [] # 제목
contents_list = [] # 게시글 내용
contents_date_list = []
gall_no_list = [] # 글 번호
reply_id = [] # 댓글 아이디
reply_content = [] # 댓글 내용
reply_date = [] # 댓글 등록일

BASE = "https://gall.dcinside.com/mgallery/board/lists"

start_page = 1
Flag = True

while Flag:
    # 게시글 목록 페이지
    BASE_URL = BASE + "?id=stockus&page=" + str(start_page)

    try:
        driver.get(BASE_URL)
        sleep(1)
    except:
        # 예외 발생 시 다시 load
        continue

    # 게시글 목록의 HTML 소스 가져오기
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')

    # 모든 게시글의 정보를 찾음
    article_list = soup.find('tbody').find_all('tr')
    
    # 해당 페이지에 수집할 게시글이 있는지 확인
    has_target_article = False
    all_old = True
    
    for article in article_list:
        date_element = article.find('td', class_='gall_date')
        if not date_element:
            continue
            
        # title 속성에서 정확한 날짜/시간 가져오기
        date_title = date_element.get('title')
        
        if date_title:  # title 속성이 있는 경우 (정확한 날짜/시간 정보)
            # "2025-11-11 15:15:31" 형식을 "2025.11.11 15:15:31" 형식으로 변환
            date_str = date_title.replace('-', '.').replace(' ', ' ')  # "2025.11.11 15:15:31"
            article_date = time.strptime(date_str, "%Y.%m.%d %H:%M:%S")  # 형식에 %S 추가
        else:  # title 속성이 없는 경우
            date_text = date_element.text.strip()
            if ':' in date_text:  # "HH:MM" 형식
                hour, minute = date_text.split(':')
                today = time.localtime()
                date_str = f"{today.tm_year}.{today.tm_mon:02d}.{today.tm_mday:02d} {hour}:{minute}"
                article_date = time.strptime(date_str, "%Y.%m.%d %H:%M")
            else:  # "MM.DD" 형식
                continue
        
        # 날짜 범위 확인
        if start_date <= article_date <= end_date:
            has_target_article = True
            all_old = False
        elif article_date < start_date:
            all_old = True
        else:
            all_old = False
    
    # 모든 게시글이 수집 기간보다 이전이면 종료
    if all_old and not has_target_article:
        print(f"페이지 {start_page}: 수집 기간보다 이전 게시글만 존재. 크롤링 종료")
        Flag = False
        break
    
    # 수집 기간에 해당하는 게시글이 없으면 다음 페이지로
    if not has_target_article:
        print(f"페이지 {start_page}: 수집할 게시글 없음. 다음 페이지로 이동")
        start_page += 1
        continue

    # 게시글 수집
    for article in article_list:
        try:
            # 날짜 확인
            date_element = article.find('td', class_='gall_date')
            if not date_element:
                continue
                
            date_title = date_element.get('title')
            
            if date_title:
                date_str = date_title.replace('-', '.').replace(' ', ' ')  # "2025.11.11 15:15:31"
                article_date = time.strptime(date_str, "%Y.%m.%d %H:%M:%S")  # 형식에 %S 추가
                c_date = date_title[:19]  # "2025-11-11 15:15:31" 형식 그대로 저장
            else:
                date_text = date_element.text.strip()
                if ':' in date_text:
                    hour, minute = date_text.split(':')
                    today = time.localtime()
                    date_str = f"{today.tm_year}.{today.tm_mon:02d}.{today.tm_mday:02d} {hour}:{minute}"
                    article_date = time.strptime(date_str, "%Y.%m.%d %H:%M")
                    c_date = date_str.replace('.', '-')
                else:
                    continue
            
            # 날짜 범위에 포함되지 않으면 건너뛰기
            if not (start_date <= article_date <= end_date):
                continue
            
            #게시글의 제목을 가져오는 부분
            title = article.find('a').text
            
            #게시글의 종류(ex-일반/설문/투표/공지/등등...)
            head = article.find('td',{"class": "gall_subject"}).text
            
            if head not in ['설문','AD','공지']: #사용자들이 쓴 글이 목적이므로 광고/설문/공지 제외
                    
                #게시글 번호 찾아오기
                gall_id = article.find("td",{"class" : "gall_num"}).text
                
                if gall_id in writer_list:
                    continue
                
                #각 게시글의 주소를 찾기
                tag = article.find('a',href = True)
                content_url = "https://gall.dcinside.com" + tag['href']
                
                #게시글 load
                try:
                    driver.get(content_url)
                    sleep(1)
                    contents_soup = BeautifulSoup(driver.page_source,"html.parser")
                    
                    write_div = contents_soup.find('div', {"class": "write_div"})
                    if write_div:
                        contents = write_div.text.strip()
                    else:
                        contents = ""
                except Exception as e:
                    print(f"게시글 로드 실패: {gall_id}")
                    continue
                
                #게시글 제목과 내용을 수집
                writer_list.append(gall_id)
                title_list.append(title)
                contents_list.append(contents)
                contents_date_list.append(c_date)
                
                print(f"수집 완료 - 번호: {gall_id} | 제목: {title[:20]}... | 날짜: {c_date}")

                
                #댓글의 갯수를 파악
                reply_no = contents_soup.find_all("li",{"class" : "ub-content"})
                if len(reply_no) > 0 :
                    for r in reply_no:
                        try:
                            user_name = r.find("em").text #답글 아이디 추출
                            user_reply_date = r.find("span",{"class" : "date_time"}).text #답글 등록 날짜 추출
                            user_reply = r.find("p",{"class" : "usertxt ub-word"}).text #답글 내용 추출
                            
                            #댓글의 내용을 저장
                            gall_no_list.append(gall_id)
                            reply_id.append(user_name)
                            reply_date.append(user_reply_date)
                            reply_content.append(user_reply)

                        except: #댓글에 디시콘만 올려놓은 경우
                            continue
                
        except Exception as e:
            print(f"게시글 처리 중 오류: {str(e)}")
            continue
            
    #다음 게시글 목록 페이지로 넘어가기
    start_page += 1
    print(f"다음 페이지({start_page})로 이동")

# 브라우저 종료
driver.quit()

#수집한 데이터를 저장
print(f"\n총 {len(writer_list)}개의 게시글과 {len(reply_id)}개의 댓글을 수집했습니다.")

contents_df = pd.DataFrame({"id" : writer_list, "title" : title_list, "content" : contents_list, "date" : contents_date_list})
reply_df = pd.DataFrame({"id" : gall_no_list, "reply_id" : reply_id, "reply_content" : reply_content, "date" : reply_date})

# 기존 파일이 있으면 불러와서 합치기
if os.path.exists("contents.csv"):
    existing_contents = pd.read_csv("contents.csv", encoding='utf8')
    contents_df = pd.concat([existing_contents, contents_df], ignore_index=True)

if os.path.exists("reply.csv"):
    existing_reply = pd.read_csv("reply.csv", encoding='utf8')
    reply_df = pd.concat([existing_reply, reply_df], ignore_index=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
contents_df.to_csv("contents.csv", encoding='utf8', index=False)
reply_df.to_csv("reply.csv", encoding='utf8', index=False)

print("크롤링이 완료되었습니다!")
print(f"게시글: contents.csv ({len(contents_df)}개)")
print(f"댓글: reply.csv ({len(reply_df)}개)")
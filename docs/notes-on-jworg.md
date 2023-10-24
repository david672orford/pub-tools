# Notes About Downloading Publictions from JW.ORG

These are notes on how the links to publications and media files on JW.ORG work.

## Watchtower Study Articles Dates

* Study article dates not reflected anywhere in the web versions of the
  Watchtower on JW.ORG
* Study article dates are given in the table of contents of the epub version
* Study article dates are given in the MP3 RSS feed
* The RSS feed shows study articles started two months in the future
* You can get links to any week's articles from wol.jw.org under "Meetings"

## MEPS Document IDs

Each chapter, article, title page, table of contents etc. is assigned a MEPS 
document ID which is an integer starting with the digits of the year. Each is
also assigned a document class number. Examples include:

* 40 Watchtower study article
* 106 Meeting Workbook week

The docId and docClass are included in each document in the class of the tag
which encloses the content area. In the Epub files this is &lt;body&gt; tag.

## Link to Songbook

Sharing link to songbook in Russian:
	https://www.jw.org/finder?wtlocale=U&pub=sjjm&srcid=share
Songbook media files (January 2020, still works in January 2021):
    https://pubmedia.jw-api.org/GETPUBMEDIALINKS?output=json&pub=sjjm&fileformat=MP3%2CAAC%2CM4V%2CMP4%2C3GP&alllangs=0&langwritten=U&txtCMSLang=U
Songbook media files (January 2021):
    https://b.jw-cdn.org/apis/pub-media/GETPUBMEDIALINKS?output=json&pub=sjjm&fileformat=MP3%2CAAC%2CM4V%2CMP4%2C3GP&alllangs=0&langwritten=U&txtCMSLang=U

## Links to Videos

Link to video from Russian Meeting Workbook:
    https://www.jw.org/finder?lank=pub-jwbcov_201505_11_VIDEO&wtlocale=U

Redirects to:
	https://www.jw.org/ru/библиотека/видео/?item=pub-jwbcov_201505_11_VIDEO&appLanguage=U

Redirects to:
	https://www.jw.org/ru/библиотека/видео/#ru/mediaitems/VODBibleTeachings/pub-jwbcov_201505_11_VIDEO

Which loads:
	https://b.jw-cdn.org/apis/mediator/v1/media-items/U/pub-jwbcov_201505_11_VIDEO?clientType=www
	https://b.jw-cdn.org/apis/mediator/v1/media-items/U/pub-jwbcov_201505_11_AUDIO?clientType=www

[JW-Scripts](https://github.com/allejok96/jw-scripts) uses what seem to be old URL's. The above
URL in the old format would probabably be like this:
	https://data.jw-api.org/apis/mediator/v1/media-items/U/pub-jwbcov_201505_11_VIDEO?detailed=1&clientType=www

## Other Downloaders for JW.ORG

* [JW-Scripts](https://github.com/allejok96/jw-scripts) -- Simple Python scripts to download videos and sound recordings
* [Periodic Publication Downloader](https://github.com/mikiTesf/ppd) -- Gets the download links for the Watchtower, Awake!, and Meeting Workbook. Optionally downloads them.
* [Library API](https://github.com/BenShelton/library-api) -- Library for downloading publications and apps all written in TypeScript, JavaScript, and Vue
* [JWP](https://github.com/Dimoshka/JWP) -- Old Android app which reportedly uses the RSS feeds
* [Meeting Media Manager](https://github.com/sircharlo/meeting-media-manager) -- Full-featured program for download and playing media at meetings


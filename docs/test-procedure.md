# Test Procedure

## Meeting Loader

To perform these tests, run **flask jworg get-meeting-media** with the indicated URL's as the parameter.

* [MWB 16--22 September 2024](https://www.jw.org/finder?wtlocale=U&docid=202024323&srcid=share)
  Verify:
    * Part 1: One illustration
    * Part 7: One video
    * Part 8: Three illustrations and one video
    * Part 9: One illustration
* [Иегова хочет, чтобы собрание относилось к согрешившим так же, как он](https://www.jw.org/finder?wtlocale=U&docid=2024532&srcid=share)
  Verify:
    * Song 130
    * Three illustrations
    * Song 109
* https://www.jw.org/finder?wtlocale=U&docid=202021161&srcid=share

## Drag-and-Drop of Bare URL's

To perform these tests, drag and drop directly from this list to the Scenes tab.

* [Слушайся родителей](https://www.jw.org/finder?srcid=share&wtlocale=U&lank=pub-pk_1_VIDEO)
  Sharing URL with LANK pointing to video library, should load an MP4 file
* [Первый разговор (видео)](https://data.jw-api.org/mediator/finder?item=pub-mwbv_201803_1_VIDEO&lang=U)
  Old finder URL from the March 2018 MWB
* [Не сдавайся!](https://www.jw.org/ru/%D0%B1%D0%B8%D0%B1%D0%BB%D0%B5%D0%B9%D1%81%D0%BA%D0%B8%D0%B5-%D1%83%D1%87%D0%B5%D0%BD%D0%B8%D1%8F/%D0%B4%D0%B5%D1%82%D0%B8/%D1%81%D1%82%D0%B0%D0%BD%D1%8C-%D0%B4%D1%80%D1%83%D0%B3%D0%BE%D0%BC-%D0%B8%D0%B5%D0%B3%D0%BE%D0%B2%D1%8B/%D0%B2%D0%B8%D0%B4%D0%B5%D0%BE/%D0%BD%D0%B5-%D1%81%D0%B4%D0%B0%D0%B2%D0%B0%D0%B9%D1%81%D1%8F/)
  Link to Become Jehovah's Friend from 16--22 September 2024 MWB points to custom player
* [Секреты семейного счастья. Проявляйте любовь](https://www.jw.org/ru/%D0%B1%D0%B8%D0%B1%D0%BB%D0%B8%D0%BE%D1%82%D0%B5%D0%BA%D0%B0/%D0%B2%D0%B8%D0%B4%D0%B5%D0%BE/#ru/mediaitems/FeaturedLibraryVideos/pub-jwb-088_3_VIDEO)
  Featured video URL points to generic LANK player, should load an MP4 file
* [В то время как близится буря, держите взор на Иисусе! Будущие благословения Царства](https://www.jw.org/ru/%D0%B1%D0%B8%D0%B1%D0%BB%D0%B8%D0%BE%D1%82%D0%B5%D0%BA%D0%B0/%D0%B2%D0%B8%D0%B4%D0%B5%D0%BE/#ru/mediaitems/VODBibleTeachings/pub-jwbcov_201505_11_VIDEO)
  A different instance of the generic LANK player
* [Что представляет собой библейский курс Свидетелей Иеговы?](https://www.jw.org/finder?wtlocale=U&docid=502012131&srcid=share)
  Sharing URL pointing to an online article, should produce web view
* [Подражайте их вере. Авраам (часть 1)](https://www.jw.org/finder?wtlocale=U&docid=502800101&srcid=share)
  Verify it is loaded as a video rather than a web page

## Drag-and-Drop from JW.ORG

To perform these tests open the indicated articles and drag and drop the indicated items to the Scenes tab.

* [Расписание встречи «Наша христианская жизнь и служение» с 16 сентября по 22 сентября 2024 года](https://www.jw.org/finder?wtlocale=U&docid=202024323&srcid=share)
  Try:
    * The opening song
    * The first illustration
    * The video in part 7
    * The video in part 8
* [Иегова хочет, чтобы собрание относилось к согрешившим так же, как он](https://www.jw.org/finder?wtlocale=U&docid=2024532&srcid=share)
  Try:
    * The opening song
    * The illustration in paragraph 5
* [УРОК 01 Как вам может помочь Библия?](https://www.jw.org/finder?wtlocale=U&docid=1102021811&srcid=share)
  Try:
    * Drag and drop link under video in section 5. Verify that it uses
      the thumbnail of the girl from the brocure rather than the thumbnail
      with the young man from the video metadata.
* [](https://www.jw.org/finder?wtlocale=U&docid=202021161&srcid=share)
  Try:
     * The Become Jehovah's Friends video
     * The Whiteboard Animation video


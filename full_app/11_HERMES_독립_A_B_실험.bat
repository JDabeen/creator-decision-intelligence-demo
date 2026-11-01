@echo off
chcp 65001 > nul
cd /d "%~dp0"
title YouTube Topic A-B Comparison (v1.6)
echo 이제 A/B 비교 대상은 대본이 아니라 다음 영상 주제입니다.
echo.
echo 프로그램을 실행해 [시장과 내 채널에서 다음 콘텐츠 찾기]를 누르세요.
echo 그 다음 [Hermes 독립 웹 조사 - 다음 주제 3개 비교]를 누르면 됩니다.
echo.
call 0_START_WITH_HERMES.bat

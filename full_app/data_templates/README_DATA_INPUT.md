# YouTube Content Consultant · 수동 데이터 입력 폴더

이 폴더는 **앱 코드와 분리된 영구 데이터**입니다. 새 버전을 받아도 지우지 마세요.
CSV는 Excel/Google Sheets/메모장으로 직접 수정하거나 앱의 `데이터 입력 · Studio` 화면에서 수정할 수 있습니다.

## 1. reference_channels.csv
`channel_ref`에 `@handle`, YouTube 채널 URL, 채널 ID(UC...) 중 하나를 넣으면 됩니다.

role:
- `audience_neighbor`: YouTube Studio의 '내 시청자가 보는 다른 채널'. Pulling 주제 발견의 1차 시장 이웃.
- `korean_reference`: 운영자가 직접 추가한 한국어 영어교육/경쟁 참고 채널.
- `global_reference`: 해외 영어교육 참고 채널. 주제·지식·설명법·포맷의 Global Transfer 후보를 찾는 용도.
- `observed_suggested_source`: 내 영상이 실제로 추천된 옆자리에서 관찰된 채널. suggested_neighbors 데이터에서 자동 파생될 수 있음.

추천 시작점은 `audience_neighbor` 5~10개입니다. Studio → 분석 → 시청자층 → 내 시청자가 보는 다른 채널을 보고 직접 추가하세요.
해외 채널은 `global_reference`로 추가하면 한국 시장과 별도로 Global Transfer 후보를 찾습니다.

## 2. my_video_performance.csv
내 영상의 7일/28일/현재 성과를 틈날 때 넣습니다. 같은 video_id를 여러 행으로 기록해도 됩니다.
- measurement_day: 7 / 28 / current
- impressions, ctr_pct, avg_percentage_viewed_pct, unique_viewers, recent_10_rank 등
- leads_count: 단톡방/문의/리드 수처럼 실제 사업 성과가 있으면 기록

## 3. suggested_neighbors.csv
내 영상이 **어떤 영상 옆 추천 동영상으로 붙었는지** 기록합니다.
가능하면 source_channel_ref도 넣으세요. 이 채널은 다음 Pulling 탐색에서 실제 Audience Neighborhood 신호로 재사용할 수 있습니다.

## 4. audience_snapshots.csv
채널 전체 Audience 수치를 날짜별로 적습니다. 연령과 영어 수준은 동일시하지 않습니다.

## 5. hypotheses.csv
전략 가설은 하드코딩 규칙이 아니라 검증 중인 가설로 저장합니다.
예: `어순 재탕은 자기잠식할 수 있다`, `방법 무효화형 제목이 더 강할 수 있다`.

## 6. content_decisions.csv
추천을 채택/보류/거절한 이유를 남길 때 씁니다. 나중에 사용자 선택 자체를 학습 데이터로 쓸 수 있습니다.

중요: 비어 있는 값은 모르는 값입니다. 0으로 추정해서 넣지 마세요.

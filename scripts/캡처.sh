#!/usr/bin/env bash
# 레퍼런스 사이트를 그림으로 찍는다 · 04 DESIGN
#
#   bash 캡처.sh {작업폴더} {주소} [{주소} ...]
#   bash 캡처.sh {작업폴더} --폰 {주소} [...]     폭을 폰 크기로
#
# 왜 필요한가.
#   웹페이지를 그냥 열면 글자만 오고 그림이 사라진다.
#   색도 글씨 크기도 여백도 안 보인다. 그래서 04 가 값을 지어내게 된다.
#   그림으로 찍어두면 실제로 볼 수 있다.
#
# 아무것도 안 깐다. 이미 깔린 크롬 계열 브라우저를 쓴다.
# 없으면 멈추지 않고 「사람에게 캡처를 청하라」고 알려준다.
#
# ※ 변수 이름은 영문으로 쓴다. bash 는 한글 변수명을 못 받는다 (zsh 는 된다).
set -e

KB_PATH=""
WIDTH=1440
HEIGHT=2600
URLS=()

for arg in "$@"; do
  case "$arg" in
    --폰)  WIDTH=390;  HEIGHT=1800 ;;
    --*)   echo "모르는 선택지입니다: $arg"; exit 1 ;;
    http://*|https://*) URLS+=("$arg") ;;
    *)
      if [ -z "$KB_PATH" ]; then KB_PATH="$arg"
      else echo "주소는 http 로 시작해야 합니다: $arg"; exit 1
      fi ;;
  esac
done

if [ -z "$KB_PATH" ] || [ ${#URLS[@]} -eq 0 ]; then
  echo "사용법:  bash 캡처.sh {작업폴더} {주소} [{주소} ...]"
  exit 1
fi

KB_PATH="${KB_PATH/#\~/$HOME}"
if [ ! -d "$KB_PATH" ]; then
  echo "작업 폴더가 안 보입니다.  $KB_PATH"
  exit 1
fi

# 깔린 브라우저를 순서대로 찾는다. 크롬 계열이면 무엇이든 된다.
BROWSER=""
for cand in \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary" \
  "/Applications/Chromium.app/Contents/MacOS/Chromium" \
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" \
  "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser" \
  "/Applications/Arc.app/Contents/MacOS/Arc"
do
  [ -x "$cand" ] && { BROWSER="$cand"; break; }
done

# 못 찾아도 여기서 스킬이 멈추면 안 된다. 사람에게 청하는 길로 넘긴다.
if [ -z "$BROWSER" ]; then
  echo "브라우저를못찾음"
  echo "크롬 계열 브라우저가 안 보입니다. 자동으로는 못 찍습니다."
  echo "사용자에게 화면 캡처를 직접 찍어 달라고 청하세요."
  exit 3
fi

OUT_DIR="$KB_PATH/outputs/04-design/.kb/레퍼런스"
mkdir -p "$OUT_DIR"

echo "찍는 데 씁니다: $(basename "$(dirname "$(dirname "$(dirname "$BROWSER")")")")"
echo

i=0
FAILED=0
for url in "${URLS[@]}"; do
  i=$((i + 1))
  host="$(echo "$url" | sed -E 's#^https?://##; s#/.*$##; s#[^A-Za-z0-9.-]#_#g')"
  out="$OUT_DIR/$(printf '%02d' "$i")-${host}.png"

  # 오류 메시지는 버린다. 크롬이 맥에서 늘 뱉는 잡소리라 화면만 어지럽힌다.
  "$BROWSER" --headless --disable-gpu --hide-scrollbars \
    --window-size="${WIDTH},${HEIGHT}" \
    --virtual-time-budget=12000 \
    --screenshot="$out" "$url" >/dev/null 2>&1 || true

  if [ ! -f "$out" ]; then
    echo "✕ $url"
    echo "    못 찍었습니다"
    FAILED=1
    continue
  fi

  bytes="$(wc -c < "$out" | tr -d ' ')"
  echo "○ $url"
  echo "    $out"
  # 아주 작으면 빈 화면이거나 오류 페이지다. 사람 눈으로 볼 필요가 있다.
  if [ "$bytes" -lt 40000 ]; then
    echo "    ⚠ 파일이 작습니다 (${bytes}바이트). 빈 화면이거나 「없는 주소」일 수 있습니다"
    echo "      열어서 확인하고, 오류 화면이면 값을 뽑지 마세요"
  fi
done

echo
echo "찍은 것을 열어서 보세요. 열어봐야 색과 짜임새가 읽힙니다."
echo "★ 이 그림은 남의 저작물입니다. 값만 뽑고 산출물 폴더로 옮기지 마세요."
exit $FAILED

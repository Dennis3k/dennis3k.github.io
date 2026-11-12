#!/bin/bash
# Напоминание перед ответом: клипы идут через скилл struktura-klipa.
input=$(cat)
if echo "$input" | grep -qiE 'клип|кадр|промт|промпт|сценар|скил|тайминг|omniflash|seedance|omnihuman|sync\.so|syncso|заказчи|раскадров|референс|ChatGPT|Nano Banana|монтаж'; then
  echo "НАПОМИНАНИЕ: перед ответом открой .claude/skills/struktura-klipa/SKILL.md и файл по теме (promty.md с чеклистом, tayming.md, chatgpt-perenos.md), сверь ответ с чеклистом, запиши новую правку в скилл и закоммить."
fi
exit 0

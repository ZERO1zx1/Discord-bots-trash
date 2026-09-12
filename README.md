# Discord Bots Trash

Discord bot туршилт, хуучин төсөл болон дахин ашиглаж болох bot-уудыг цэвэрлэж,
тус тусад нь салгасан цуглуулга.

## Төслүүд

| Хавтас | Технологи | Тайлбар |
| --- | --- | --- |
| [`bots/gurten-lgc`](bots/gurten-lgc) | Python, discord.py | Economy, leveling, moderation, games зэрэг олон cog-той үндсэн бот |
| [`bots/face-rating-bot`](bots/face-rating-bot) | Python, discord.py | Зураг боловсруулах болон face-rating туршилтын бот |
| [`bots/combined`](bots/combined) | Python + JavaScript | Нэг санааны Python болон discord.js хэрэгжүүлэлтүүд |
| [`tools`](tools) | Python | Төсөл үүсгэгч болон хуучин launcher хэрэгслүүд |

Төсөл бүр бие даасан хавтас тул тухайн хавтасны `README.md`,
`requirements.txt` эсвэл `package.json`-ийг ашиглан ажиллуулна.

## Аюулгүй байдал

Discord bot token болон API key-г source code-д бичихгүй. Өөрийн `.env` файлыг
локал орчинд үүсгэнэ. `.env`, database, cache болон editor-ийн тохиргоонууд Git-д
орохгүй байхаар тохируулсан.

## Хассан локал файлууд

Repository-г хөнгөн, clone хийхэд тохиромжтой байлгахын тулд дараах файлуудыг
эх хавтсанд нь үлдээсэн:

- `Gurten-LGC.zip` архив;
- runtime SQLite database-ууд;
- Python cache болон nested Git history;
- Windows system font-ийн хуулбарууд;
- ойролцоогоор 670 MB хэмжээтэй GIF asset сан.

Эдгээр asset шаардлагатай бол тусдаа release эсвэл Git LFS ашиглан хадгалах нь
зөв.

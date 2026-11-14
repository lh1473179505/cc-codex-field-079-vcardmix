# vcardmix

通讯录导出夹杂着 vCard 3.0 和 4.0，还有折行和残缺卡片。同一邮箱要以较新的 REV 为准合成一条。

```
python -m vcardmix ingest --cards fixtures/cards --out <out>
python -m vcardmix verify --out <out> --expect fixtures/expected/contacts.json
```

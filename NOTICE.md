# 来源与权利说明

本仓库包括项目适配代码、研究笔记、第三方补丁和运行证据。不同部分的权利与许可需要分别处理；本次整理没有给整个仓库附加统一的开源许可证。

- 参考项目：[chocotan/a7c2-re](https://github.com/chocotan/a7c2-re)，固定提交 `25efb56d7f0c69355f9225d1da50454207532e7f`。参考 QEMU 补丁及清单保存在 `outputs/sony-a7iv-qemu/source/qemu-reference/`；应结合上游许可与文件声明使用。
- QEMU 源码与衍生补丁遵循对应上游文件的许可。完整上游 QEMU 源码不随本仓库分发。
- Sony 开源内核参考：[Sony-ILCE-7M4-Linux](https://github.com/DavidBuchanan314/Sony-ILCE-7M4-Linux)，固定提交 `fa5c6f6aba58f675691e5adf291b155b76e6e93e`。内核许可证副本为 `outputs/sony-a7iv-qemu/source/COPYING.kernel`。
- 固件解析工具参考：[ma1co/fwtool.py](https://github.com/ma1co/fwtool.py)，记录的固定提交为 `3955d7890fc38daf942bb52827599bfe35de4a14`。完整工具与依赖需按各自许可另行准备。
- Sony 固件、界面文字、字体、音效等资源的权利属于相应权利人。仓库不包含完整固件、分区、专有应用、字体或可刷写更新包；截图、诊断及短音频样本用于记录具体实验，不赋予这些资源额外的再分发许可。

项目与 Sony 无隶属关系。仓库中关于修改样本启动的结论只覆盖文档注明的虚拟环境验证，不代表实体设备升级兼容性。

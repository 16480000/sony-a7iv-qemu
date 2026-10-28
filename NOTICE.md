# 来源与权利说明

本仓库的原创贡献使用根目录 [MIT License](LICENSE)。已有文件头、上游许可证或以下第三方权利说明覆盖的部分继续遵循各自许可；根目录 MIT 不用于重新许可 QEMU/Linux 衍生补丁、Sony 资源或第三方证据内容。

- 参考项目：[chocotan/a7c2-re](https://github.com/chocotan/a7c2-re)，固定提交 `25efb56d7f0c69355f9225d1da50454207532e7f`。该提交根目录使用 MIT，许可证及 chocotan 署名副本见 [a7c2-re.MIT.txt](third_party/licenses/a7c2-re.MIT.txt)。参考 QEMU 补丁及清单保存在 `outputs/sony-a7iv-qemu/source/qemu-reference/`；修改上游 GPL 文件的补丁仍应遵循相应文件的许可。
- QEMU 源码与衍生补丁遵循对应上游文件的许可。完整上游 QEMU 源码不随本仓库分发。
- Sony 开源内核参考：[Sony-ILCE-7M4-Linux](https://github.com/DavidBuchanan314/Sony-ILCE-7M4-Linux)，固定提交 `fa5c6f6aba58f675691e5adf291b155b76e6e93e`。内核许可证副本为 `outputs/sony-a7iv-qemu/source/COPYING.kernel`。
- 固件解析工具参考：[ma1co/fwtool.py](https://github.com/ma1co/fwtool.py)，记录的固定提交为 `3955d7890fc38daf942bb52827599bfe35de4a14`。完整工具与依赖需按各自许可另行准备。
- Sony 固件、界面文字、字体、音效等资源的权利属于相应权利人。仓库不包含完整固件、分区、专有应用、字体或可刷写更新包；截图、诊断及短音频样本用于记录具体实验，不赋予这些资源额外的再分发许可。

项目与 Sony 无隶属关系。仓库中关于修改样本启动的结论只覆盖文档注明的虚拟环境验证，不代表实体设备升级兼容性。

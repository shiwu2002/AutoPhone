// ========== Excel 批量任务功能 ==========

// 全局变量存储选中的文件
let selectedFile = null;

// 初始化拖放区域
function initDropZone() {
    const dropZone = document.getElementById('dropZone');

    if (!dropZone) return;

    // 拖拽进入
    dropZone.addEventListener('dragenter', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    // 拖拽经过
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
    });

    // 拖拽离开
    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
    });

    // 文件放下
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileDrop(files[0]);
        }
    });
}

// 处理拖放的文件
function handleFileDrop(file) {
    const validTypes = [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel',
        'application/excel',
        'text/plain'
    ];

    const validExtensions = ['.xlsx', '.xls', '.txt'];
    const fileExt = '.' + file.name.split('.').pop().toLowerCase();

    if (!validExtensions.includes(fileExt)) {
        showExcelMessage('不支持的文件格式，请选择 .xlsx, .xls 或 .txt 文件', true);
        return;
    }

    selectedFile = file;
    updateFileDisplay();
}

// 处理文件选择
function handleFileSelect(event) {
    const files = event.target.files;
    if (files.length > 0) {
        selectedFile = files[0];
        updateFileDisplay();
    }
}

// 更新文件显示
function updateFileDisplay() {
    const display = document.getElementById('fileSelectedDisplay');
    const nameSpan = document.getElementById('selectedFileName');
    const dropZone = document.getElementById('dropZone');

    if (selectedFile) {
        nameSpan.textContent = `${selectedFile.name} (${formatFileSize(selectedFile.size)})`;
        display.style.display = 'flex';
        dropZone.style.display = 'none';
    }
}

// 移除选中的文件
function removeSelectedFile() {
    selectedFile = null;
    document.getElementById('fileSelectedDisplay').style.display = 'none';
    document.getElementById('dropZone').style.display = 'block';
    document.getElementById('fileInputHidden').value = '';
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// 上传文件到服务器
async function uploadFileToServer(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            return data.file_path;
        } else {
            throw new Error(data.error || '上传失败');
        }
    } catch (error) {
        throw new Error(`文件上传失败：${error.message}`);
    }
}

// 获取当前文件路径（支持上传文件）
async function getCurrentFilePath() {
    // 必须有选中的文件
    if (!selectedFile) {
        throw new Error('请选择文件');
    }

    showExcelMessage('正在上传文件...');
    const filePath = await uploadFileToServer(selectedFile);
    return filePath;
}

// 显示 Excel 消息
function showExcelMessage(message, isError = false) {
    const messageArea = document.getElementById('excelMessageArea');
    messageArea.innerHTML = `
        <div class="alert ${isError ? 'alert-error' : 'alert-info'}">
            ${message}
        </div>
    `;
    setTimeout(() => {
        messageArea.innerHTML = '';
    }, 5000);
}

// 预览 Excel 文件内容
async function previewExcel() {
    const previewBtn = document.getElementById('previewBtn');
    previewBtn.disabled = true;
    previewBtn.innerHTML = '<span class="loading"></span>加载中...';

    try {
        // 获取文件路径（上传文件）
        const filePath = await getCurrentFilePath();

        const response = await fetch(`${API_BASE}/excel/preview`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ file: filePath })
        });

        const data = await response.json();

        if (data.success) {
            const previewArea = document.getElementById('previewArea');
            const previewContent = document.getElementById('previewContent');

            let html = `<div style="margin-bottom: 10px;"><strong>列:</strong> ${data.columns.join(', ')}</div>`;
            html += `<div style="margin-bottom: 10px;"><strong>问题数:</strong> ${data.count}</div>`;
            html += `<div style="margin-bottom: 10px;"><strong>问题列:</strong> ${data.question_column}</div>`;
            html += '<hr style="margin: 15px 0; border: none; border-top: 1px solid #ddd;">';
            html += '<div style="margin-bottom: 10px;"><strong>问题列表:</strong></div>';
            html += '<ol style="padding-left: 20px;">';

            const previewQuestions = data.questions.slice(0, 10);
            for (const q of previewQuestions) {
                html += `<li style="margin-bottom: 8px; color: #333;">${escapeHtml(q)}</li>`;
            }
            html += '</ol>';

            if (data.questions.length > 10) {
                html += `<div style="margin-top: 10px; color: #999; font-size: 13px;">... 还有 ${data.questions.length - 10} 个问题</div>`;
            }

            previewContent.innerHTML = html;
            previewArea.style.display = 'block';
            showExcelMessage(`✅ 成功加载 ${data.count} 个问题`);
        } else {
            showExcelMessage(`❌ 预览失败：${data.error}`, true);
            document.getElementById('previewArea').style.display = 'none';
        }
    } catch (error) {
        showExcelMessage(`❌ 预览请求失败：${error.message}`, true);
    } finally {
        previewBtn.disabled = false;
        previewBtn.innerHTML = '📋 预览';
    }
}

// 执行 Excel 批量任务
async function executeExcelBatch() {
    const taskInput = document.getElementById('excelTaskInput');
    const saveScreenshotsInput = document.getElementById('saveScreenshotsInput');
    const embedScreenshotsInput = document.getElementById('embedScreenshotsInput');

    const task = taskInput.value.trim();

    if (!task) {
        showExcelMessage('请输入任务模板', true);
        return;
    }

    // 获取文件路径（支持上传或路径输入）
    let filePath;
    try {
        filePath = await getCurrentFilePath();
    } catch (error) {
        showExcelMessage(error.message, true);
        return;
    }

    const executeBtn = document.getElementById('excelBatchBtn');
    executeBtn.disabled = true;
    executeBtn.innerHTML = '<span class="loading"></span>执行中...';

    document.getElementById('excelResultArea').style.display = 'block';
    document.getElementById('excelResultContent').innerHTML = '';
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('progressText').textContent = '0 / 0';
    document.getElementById('currentQuestion').textContent = '';

    try {
        const response = await fetch(`${API_BASE}/excel/batch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file: filePath,
                task,
                save_screenshots: saveScreenshotsInput.checked,
                embed_screenshot: embedScreenshotsInput.checked
            })
        });

        const data = await response.json();

        if (data.success) {
            const stats = data.statistics;
            const outputMsg = `输出文件：<a href="#" onclick="downloadFile('${data.output_file}')" style="color: #1976d2;">${data.output_file}</a>`;

            document.getElementById('excelResultContent').innerHTML = `
                <div style="margin-bottom: 15px;">
                    <strong>总问题数:</strong> ${stats.total} |
                    <strong style="color: #4caf50;">成功:</strong> ${stats.success} |
                    <strong style="color: #f44336;">失败:</strong> ${stats.failed}
                </div>
                <div style="margin-bottom: 15px;">${outputMsg}</div>
                <div style="max-height: 300px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 6px;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead style="background: #f5f7fa; position: sticky; top: 0;">
                            <tr>
                                <th style="padding: 10px; text-align: left; border-bottom: 1px solid #ddd;">问题</th>
                                <th style="padding: 10px; text-align: left; border-bottom: 1px solid #ddd;">状态</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.results.map((r, i) => `
                                <tr style="${i % 2 === 0 ? 'background: #fff' : 'background: #f9f9f9'}">
                                    <td style="padding: 10px; border-bottom: 1px solid #eee; max-width: 400px; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(r.question)}</td>
                                    <td style="padding: 10px; border-bottom: 1px solid #eee;">
                                        <span class="status-badge ${r.success ? 'status-success' : 'status-failed'}">
                                            ${r.success ? '成功' : '失败'}
                                        </span>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;

            document.getElementById('progressBar').style.width = '100%';
            document.getElementById('progressText').textContent = `${stats.total} / ${stats.total}`;
            document.getElementById('currentQuestion').textContent = '执行完成！';

            showExcelMessage(`✅ 批量任务执行完成！成功 ${stats.success}/${stats.total}`);
            loadHistory();
            loadStats();
        } else {
            showExcelMessage(`❌ 执行失败：${data.error}`, true);
            document.getElementById('currentQuestion').textContent = '执行失败';
        }
    } catch (error) {
        showExcelMessage(`❌ 执行请求失败：${error.message}`, true);
        document.getElementById('currentQuestion').textContent = '请求失败';
    } finally {
        executeBtn.disabled = false;
        executeBtn.innerHTML = '▶️ 开始执行';
    }
}

// 下载文件辅助函数
function downloadFile(filePath) {
    alert(`文件已保存到：${filePath}\n\n请在文件管理器中打开该文件查看结果。`);
    return false;
}

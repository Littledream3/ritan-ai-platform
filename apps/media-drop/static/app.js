(() => {
  'use strict';

  const $ = id => document.getElementById(id);
  const limits = {maxFiles:500,maxBatch:20*1024**3,maxPhoto:25*1024**2,maxVideo:750*1024**2};
  const state = {items:[],batchId:'',token:'',uploading:false};
  const acceptedImageTypes = new Set(['image/jpeg','image/png','image/webp','image/heic','image/heif']);
  const acceptedVideoTypes = new Set(['video/mp4','video/quicktime','video/webm','video/x-m4v']);

  function formatBytes(bytes) {
    if(bytes<1024)return `${bytes} B`;if(bytes<1024**2)return `${(bytes/1024).toFixed(1)} KB`;if(bytes<1024**3)return `${(bytes/1024**2).toFixed(1)} MB`;return `${(bytes/1024**3).toFixed(2)} GB`;
  }
  function toast(message){const box=$('toast');box.textContent=message;box.classList.add('visible');clearTimeout(toast.timer);toast.timer=setTimeout(()=>box.classList.remove('visible'),2500);}
  function isVideo(file){return file.type.startsWith('video/')||/\.(mp4|mov|webm|m4v)$/i.test(file.name);}
  function isImage(file){return file.type.startsWith('image/')||/\.(jpe?g|png|webp|heic|heif)$/i.test(file.name);}
  function allowed(file){return acceptedImageTypes.has(file.type)||acceptedVideoTypes.has(file.type)||isImage(file)||isVideo(file);}
  function totalSize(){return state.items.reduce((sum,item)=>sum+item.file.size,0);}
  function revokeItem(item){if(item.previewUrl)URL.revokeObjectURL(item.previewUrl);}

  function addFiles(fileList) {
    if(state.uploading)return;
    const incoming=Array.from(fileList),errors=[];
    for(const file of incoming){
      if(state.items.length>=limits.maxFiles){errors.push('单批最多选择 500 个文件');break;}
      if(!allowed(file)){errors.push(`${file.name}：格式不支持`);continue;}
      const video=isVideo(file),maximum=video?limits.maxVideo:limits.maxPhoto;
      if(file.size>maximum){errors.push(`${file.name}：超过${video?'750 MB':'25 MB'}限制`);continue;}
      if(totalSize()+file.size>limits.maxBatch){errors.push('单批总大小不能超过 20 GB');break;}
      const signature=`${file.name}|${file.size}|${file.lastModified}`;
      if(state.items.some(item=>item.signature===signature)){continue;}
      state.items.push({id:crypto.randomUUID(),signature,file,kind:video?'video':'image',status:'queued',progress:0,error:'',previewUrl:!video&&file.type!=='image/heic'&&file.type!=='image/heif'?URL.createObjectURL(file):''});
    }
    if(errors.length){$('uploadError').textContent=errors.slice(0,3).join('；');toast('部分文件未加入队列');}else{$('uploadError').textContent='';}
    renderQueue();
  }

  function renderQueue(){
    const hasFiles=state.items.length>0;$('dropZone').hidden=hasFiles;$('queuePanel').hidden=!hasFiles;if(!hasFiles)return;
    $('selectedCount').textContent=String(state.items.length);$('selectedSize').textContent=formatBytes(totalSize());
    $('fileList').innerHTML=state.items.map(item=>{
      const status=item.status==='success'?'<strong>已保存</strong>':item.status==='uploading'?`上传中 ${Math.round(item.progress)}%`:item.status==='error'?`<strong class="failed">失败</strong><span>${escapeHtml(item.error)}</span>`:'等待上传';
      const thumb=item.previewUrl?`<div class="file-thumb"><img src="${item.previewUrl}" alt=""></div>`:`<div class="file-thumb ${item.kind==='video'?'video':''}">${item.kind==='image'?'IMG':''}</div>`;
      return `<article class="file-item ${item.status}" data-item-id="${item.id}">${thumb}<div class="file-info"><strong class="file-name" title="${escapeHtml(item.file.name)}">${escapeHtml(item.file.name)}</strong><div class="file-meta"><span>${item.kind==='video'?'视频':'图片'}</span><span>${formatBytes(item.file.size)}</span></div><div class="file-progress"><i style="width:${item.status==='success'?100:item.progress}%"></i></div></div><div class="file-status">${status}${!state.uploading&&item.status!=='success'?`<button class="remove-file" data-remove="${item.id}" type="button">移除</button>`:''}</div></article>`;
    }).join('');
    document.querySelectorAll('[data-remove]').forEach(button=>button.addEventListener('click',()=>removeItem(button.dataset.remove)));
    updateOverall();$('uploadButton').disabled=state.uploading||!state.items.some(item=>item.status!=='success');$('uploadButton').textContent=state.items.some(item=>item.status==='error')?'重试失败文件':'上传并保存到服务器';
  }
  function escapeHtml(value){return value.replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));}
  function removeItem(id){const index=state.items.findIndex(item=>item.id===id);if(index<0)return;revokeItem(state.items[index]);state.items.splice(index,1);renderQueue();}
  function updateOverall(){
    const total=totalSize()||1,progressed=state.items.reduce((sum,item)=>sum+item.file.size*(item.status==='success'?1:item.progress/100),0),percent=Math.min(100,progressed/total*100),success=state.items.filter(item=>item.status==='success').length;
    $('overallBar').style.width=`${percent}%`;$('overallText').textContent=state.uploading?`${success}/${state.items.length} 已保存 · ${Math.round(percent)}%`:success===state.items.length&&success?`${success} 个文件已保存`:'等待上传';
  }

  async function createBatch(){
    if(state.batchId)return;
    const response=await fetch('api/batches',{method:'POST'}),data=await response.json();if(!response.ok)throw new Error(data.detail||'无法创建上传批次');state.batchId=data.batch.id;state.token=data.upload_token;
  }
  function uploadOne(item){
    return new Promise((resolve,reject)=>{const form=new FormData();form.append('file',item.file,item.file.name);const xhr=new XMLHttpRequest();xhr.open('POST',`api/batches/${state.batchId}/files`);xhr.setRequestHeader('X-Upload-Token',state.token);item.status='uploading';item.progress=0;renderQueue();xhr.upload.onprogress=event=>{if(event.lengthComputable){item.progress=event.loaded/event.total*100;const bar=document.querySelector(`[data-item-id="${item.id}"] .file-progress i`);if(bar)bar.style.width=`${item.progress}%`;updateOverall();}};xhr.onload=()=>{let data={};try{data=JSON.parse(xhr.responseText);}catch(_){}if(xhr.status>=200&&xhr.status<300){item.status='success';item.progress=100;item.error='';resolve(data);}else{item.status='error';item.error=data.detail||`上传失败（${xhr.status}）`;reject(new Error(item.error));}renderQueue();};xhr.onerror=()=>{item.status='error';item.error='网络中断，请重试';renderQueue();reject(new Error(item.error));};xhr.send(form);});
  }
  async function runPool(items,concurrency){let cursor=0;async function worker(){while(cursor<items.length){const item=items[cursor++];try{await uploadOne(item);}catch(_){}}}await Promise.all(Array.from({length:Math.min(concurrency,items.length)},worker));}
  async function completeBatch(){const response=await fetch(`api/batches/${state.batchId}/complete`,{method:'POST',headers:{'X-Upload-Token':state.token}}),data=await response.json();if(!response.ok)throw new Error(data.detail||'无法完成批次');return data.batch;}

  async function startUpload(){
    if(state.uploading)return;const pending=state.items.filter(item=>item.status!=='success');if(!pending.length)return;state.uploading=true;$('uploadError').textContent='';renderQueue();
    try{await createBatch();await runPool(pending,2);const failed=state.items.filter(item=>item.status==='error');if(failed.length){$('uploadError').textContent=`${failed.length} 个文件上传失败，可点击按钮重试`;return;}const batch=await completeBatch();showSuccess(batch);}
    catch(error){$('uploadError').textContent=error.message;}
    finally{state.uploading=false;renderQueue();}
  }
  function showSuccess(batch){$('uploadPanel').hidden=true;$('successPanel').hidden=false;$('batchCode').textContent=batch.id;$('savedFiles').textContent=String(batch.file_count);$('savedSize').textContent=formatBytes(batch.total_bytes);window.scrollTo({top:0,behavior:'smooth'});toast('全部文件已保存');}
  function reset(){state.items.forEach(revokeItem);state.items=[];state.batchId='';state.token='';state.uploading=false;$('successPanel').hidden=true;$('uploadPanel').hidden=false;$('uploadError').textContent='';$('fileInput').value='';renderQueue();}

  $('selectFiles').addEventListener('click',()=>$('fileInput').click());$('addMore').addEventListener('click',()=>$('fileInput').click());$('fileInput').addEventListener('change',function(){addFiles(this.files);this.value='';});$('clearQueue').addEventListener('click',()=>{if(state.uploading)return;state.items.forEach(revokeItem);state.items=[];renderQueue();});$('uploadButton').addEventListener('click',startUpload);$('newUpload').addEventListener('click',reset);
  const dropZone=$('dropZone');['dragenter','dragover'].forEach(name=>dropZone.addEventListener(name,event=>{event.preventDefault();dropZone.classList.add('dragging');}));['dragleave','drop'].forEach(name=>dropZone.addEventListener(name,event=>{event.preventDefault();dropZone.classList.remove('dragging');}));dropZone.addEventListener('drop',event=>addFiles(event.dataTransfer.files));
  window.addEventListener('beforeunload',()=>state.items.forEach(revokeItem));
})();

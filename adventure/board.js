export default function(component) {
  const {parentElement, data, setTriggerValue} = component;
  const board = parentElement.querySelector('.game-board');
  const canvas = board.querySelector('canvas');
  const ctx = canvas.getContext('2d');
  const hint = board.querySelector('.board-hint');
  hint.textContent = data.phase === 'COMBAT'
    ? '战斗快捷键：1 重击 · 2 回响 · 3 防御 · 4 药剂 · 5 等待'
    : '点击相邻格 · 点击地图后可用方向键 / WASD · E 互动';
  let pending = false;
  let disposed = false;
  const img = new Image();
  img.onload = () => {
    if (disposed) return;
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(img,0,0,640,640);
    if (data.phase === 'EXPLORING') {
      ctx.strokeStyle = '#f9d88e99'; ctx.lineWidth = 2;
      for (const [x,y] of data.neighbors) ctx.strokeRect(x*64+2,y*64+2,60,60);
    }
  };
  img.src = data.image;
  const send = (action) => {
    if (pending || data.phase === 'RESULT') return;
    pending = true;
    setTriggerValue('action', {...action, revision:data.revision});
  };
  const click = (event) => {
    board.focus({preventScroll:true});
    if (data.phase !== 'EXPLORING') return;
    const r = canvas.getBoundingClientRect();
    send({type:'move', x:Math.floor((event.clientX-r.left)/r.width*10),
                       y:Math.floor((event.clientY-r.top)/r.height*10)});
  };
  const keydown = (event) => {
    if (event.repeat) return;
    const key = event.key.toLowerCase();
    const dir = {arrowup:[0,-1],w:[0,-1],arrowdown:[0,1],s:[0,1],
      arrowleft:[-1,0],a:[-1,0],arrowright:[1,0],d:[1,0]}[key];
    if (dir && data.phase === 'EXPLORING') {
      event.preventDefault(); send({type:'move',x:data.x+dir[0],y:data.y+dir[1]});
    } else if (key === 'e' && data.interaction && data.phase === 'EXPLORING') {
      event.preventDefault(); send({type:'interact',id:data.interaction});
    } else if (data.phase === 'COMBAT') {
      const action = {'1':'burst','2':'flow','3':'guard','4':'potion','5':'wait'}[key];
      if (action) {event.preventDefault(); send({type:'act',action});}
    }
  };
  canvas.addEventListener('click',click);
  board.addEventListener('keydown',keydown);
  return () => {
    disposed = true;
    canvas.removeEventListener('click',click);
    board.removeEventListener('keydown',keydown);
  };
}

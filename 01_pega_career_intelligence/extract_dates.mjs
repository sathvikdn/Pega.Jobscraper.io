import fs from 'fs';

const html = fs.readFileSync('Pega_Career_Intelligence_Hub.html', 'utf8');
const text = html
  .replace(/<script[\s\S]*?<\/script>/g, ' ')
  .replace(/<[^>]+>/g, ' ')
  .replace(/&amp;/g, '&')
  .replace(/&rarr;/g, '->')
  .replace(/\s+/g, ' ');

const months = 'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|June|July|August|September|October|November|December';

function norm(m) {
  const map = { January: 'Jan', February: 'Feb', March: 'Mar', April: 'Apr', June: 'Jun', July: 'Jul', August: 'Aug', September: 'Sep', October: 'Oct', November: 'Nov', December: 'Dec' };
  return map[m] || m;
}

const joinRe = new RegExp(`\\b(from|since|joined|joining)\\s+(?:the\\s+)?(${months})\\.?\\s+(\\d{4})`, 'gi');
const arrInRe = new RegExp(`\\((${months})\\s+(\\d{4}),`, 'gi');
const leaveRe = new RegExp(`\\b(LWD:?|left|last working day:?|ended|ending)\\s*[:\\-]?\\s*(${months})\\.?\\s*(\\d{1,2})?,?\\s*(\\d{4})`, 'gi');

let joins = [];
let m;
while ((m = joinRe.exec(text))) {
  joins.push({ month: norm(m[2]), year: +m[3], ctx: text.slice(Math.max(0, m.index - 60), m.index + 40).trim() });
}
while ((m = arrInRe.exec(text))) {
  joins.push({ month: norm(m[1]), year: +m[2], ctx: text.slice(Math.max(0, m.index - 60), m.index + 40).trim() });
}
let leaves = [];
while ((m = leaveRe.exec(text))) {
  leaves.push({ month: norm(m[2]), year: +(m[4] || m[3]), ctx: text.slice(Math.max(0, m.index - 60), m.index + 40).trim() });
}

fs.writeFileSync('dates_extracted.json', JSON.stringify({ joins, leaves }, null, 2));
console.log('joins:', joins.length, 'leaves:', leaves.length);

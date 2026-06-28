// SmartNote —— 移植自 Python 版 RichNote 的智能着色（set_smart_text）
// 行首判定（标题/警示/结论）+ 行内 token（数字加粗、负面评级词标红）
import { View, Text } from '@tarojs/components';
import './SmartNote.scss';

const POS_KEYS = ['省', '更划算', '健康', '合法', '✅', '推荐', '增加', '高于平均'];
const NEG_KEYS = ['亏', '违法', '危险', '高利贷', '失控', '⚠', '更高', '减少', '缺口', '入不敷出', '低于10', '不建议'];
const CONCL_PREFIX = ['→', '✅', '✓', '✗', '▶', '👉'];
const NEG_WORDS = ['偏高', '高利贷', '极高', '违法', '危险', '失控', '吃紧', '盖不住', '越还越多', '不建议', '红线', '入不敷出'];

// 把一行拆成 token（数字 / 负面评级词 / 普通文本），各着色
function tokenize(line: string): { t: string; c: string }[] {
  const re = /(\d[\d,]*\.?\d*|偏高|高利贷|极高|违法|危险|失控|吃紧|盖不住|越还越多|不建议|红线|入不敷出)/g;
  const out: { t: string; c: string }[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(line)) !== null) {
    if (m.index > last) out.push({ t: line.slice(last, m.index), c: '' });
    out.push({ t: m[0], c: /\d/.test(m[0]) ? 'num' : 'bad' });
    last = m.index + m[0].length;
  }
  if (last < line.length) out.push({ t: line.slice(last), c: '' });
  return out.length ? out : [{ t: line, c: '' }];
}

function lineClass(line: string): string {
  if (!line) return '';
  if (line[0] === '【') return 'h';
  if (line.startsWith('█')) return 'h';
  if (line.startsWith('⚠')) return 'warn';
  if (CONCL_PREFIX.includes(line[0])) {
    if (POS_KEYS.some((k) => line.includes(k))) return 'big';
    if (NEG_KEYS.some((k) => line.includes(k))) return 'bigbad';
    return 'emph';
  }
  return '';
}

export default function SmartNote({ text }: { text: string }) {
  const lines = text.split('\n');
  return (
    <View className="smart-note">
      {lines.map((ln, i) => {
        const lc = lineClass(ln);
        if (lc) {
          return <Text className={`sn-line ${lc}`} key={i}>{ln || ' '}</Text>;
        }
        return (
          <Text className="sn-line" key={i}>
            {tokenize(ln).map((tk, j) => (
              <Text className={tk.c} key={j}>{tk.t}</Text>
            ))}
          </Text>
        );
      })}
    </View>
  );
}

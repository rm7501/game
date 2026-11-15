// يبني بيانات خريطة العالم للعبة من world-atlas (Natural Earth 1:50m)
// الناتج: public/data/world.json  (طوبولوجيا مبسطة + بيانات كل دولة)
// التشغيل: npm run build:world
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import * as topojson from 'topojson-client';
import { topology } from 'topojson-server';
import { presimplify, simplify, quantile, sphericalTriangleArea } from 'topojson-simplify';
import { geoArea, geoCentroid, geoBounds } from 'd3-geo';
import pc from 'polygon-clipping';

const require = createRequire(import.meta.url);
const src = require('world-atlas/countries-50m.json');
const R = 6371; // km

// [iso2, الاسم بالعربي, القارة]
const PLAYABLE = {
  'Zimbabwe': ['zw', 'زيمبابوي', 'AF'], 'Zambia': ['zm', 'زامبيا', 'AF'], 'Yemen': ['ye', 'اليمن', 'AS'],
  'Vietnam': ['vn', 'فيتنام', 'AS'], 'Venezuela': ['ve', 'فنزويلا', 'SA'], 'Vatican': ['va', 'الفاتيكان', 'EU'],
  'Vanuatu': ['vu', 'فانواتو', 'OC'], 'Uzbekistan': ['uz', 'أوزبكستان', 'AS'], 'Uruguay': ['uy', 'الأوروغواي', 'SA'],
  'Micronesia': ['fm', 'ميكرونيزيا', 'OC'], 'Marshall Is.': ['mh', 'جزر مارشال', 'OC'],
  'United States of America': ['us', 'الولايات المتحدة', 'NA'], 'United Kingdom': ['gb', 'المملكة المتحدة', 'EU'],
  'United Arab Emirates': ['ae', 'الإمارات', 'AS'], 'Ukraine': ['ua', 'أوكرانيا', 'EU'], 'Uganda': ['ug', 'أوغندا', 'AF'],
  'Turkmenistan': ['tm', 'تركمانستان', 'AS'], 'Turkey': ['tr', 'تركيا', 'AS'], 'Tunisia': ['tn', 'تونس', 'AF'],
  'Trinidad and Tobago': ['tt', 'ترينيداد وتوباغو', 'NA'], 'Tonga': ['to', 'تونغا', 'OC'], 'Togo': ['tg', 'توغو', 'AF'],
  'Timor-Leste': ['tl', 'تيمور الشرقية', 'AS'], 'Thailand': ['th', 'تايلاند', 'AS'], 'Tanzania': ['tz', 'تنزانيا', 'AF'],
  'Tajikistan': ['tj', 'طاجيكستان', 'AS'], 'Taiwan': ['tw', 'تايوان', 'AS'], 'Syria': ['sy', 'سوريا', 'AS'],
  'Switzerland': ['ch', 'سويسرا', 'EU'], 'Sweden': ['se', 'السويد', 'EU'], 'eSwatini': ['sz', 'إسواتيني', 'AF'],
  'Suriname': ['sr', 'سورينام', 'SA'], 'S. Sudan': ['ss', 'جنوب السودان', 'AF'], 'Sudan': ['sd', 'السودان', 'AF'],
  'Sri Lanka': ['lk', 'سريلانكا', 'AS'], 'Spain': ['es', 'إسبانيا', 'EU'], 'South Korea': ['kr', 'كوريا الجنوبية', 'AS'],
  'South Africa': ['za', 'جنوب أفريقيا', 'AF'], 'Somalia': ['so', 'الصومال', 'AF'], 'Solomon Is.': ['sb', 'جزر سليمان', 'OC'],
  'Slovakia': ['sk', 'سلوفاكيا', 'EU'], 'Slovenia': ['si', 'سلوفينيا', 'EU'], 'Singapore': ['sg', 'سنغافورة', 'AS'],
  'Sierra Leone': ['sl', 'سيراليون', 'AF'], 'Seychelles': ['sc', 'سيشل', 'AF'], 'Serbia': ['rs', 'صربيا', 'EU'],
  'Senegal': ['sn', 'السنغال', 'AF'], 'Saudi Arabia': ['sa', 'السعودية', 'AS'],
  'São Tomé and Principe': ['st', 'ساو تومي وبرينسيب', 'AF'], 'San Marino': ['sm', 'سان مارينو', 'EU'],
  'Samoa': ['ws', 'ساموا', 'OC'], 'St. Vin. and Gren.': ['vc', 'سانت فينسنت والغرينادين', 'NA'],
  'Saint Lucia': ['lc', 'سانت لوسيا', 'NA'], 'St. Kitts and Nevis': ['kn', 'سانت كيتس ونيفيس', 'NA'],
  'Rwanda': ['rw', 'رواندا', 'AF'], 'Russia': ['ru', 'روسيا', 'EU'], 'Romania': ['ro', 'رومانيا', 'EU'],
  'Qatar': ['qa', 'قطر', 'AS'], 'Portugal': ['pt', 'البرتغال', 'EU'], 'Poland': ['pl', 'بولندا', 'EU'],
  'Philippines': ['ph', 'الفلبين', 'AS'], 'Peru': ['pe', 'بيرو', 'SA'], 'Paraguay': ['py', 'باراغواي', 'SA'],
  'Papua New Guinea': ['pg', 'بابوا غينيا الجديدة', 'OC'], 'Panama': ['pa', 'بنما', 'NA'], 'Palau': ['pw', 'بالاو', 'OC'],
  'Pakistan': ['pk', 'باكستان', 'AS'], 'Oman': ['om', 'عُمان', 'AS'], 'Norway': ['no', 'النرويج', 'EU'],
  'North Korea': ['kp', 'كوريا الشمالية', 'AS'], 'Nigeria': ['ng', 'نيجيريا', 'AF'], 'Niger': ['ne', 'النيجر', 'AF'],
  'Nicaragua': ['ni', 'نيكاراغوا', 'NA'], 'New Zealand': ['nz', 'نيوزيلندا', 'OC'], 'Netherlands': ['nl', 'هولندا', 'EU'],
  'Nepal': ['np', 'نيبال', 'AS'], 'Nauru': ['nr', 'ناورو', 'OC'], 'Namibia': ['na', 'ناميبيا', 'AF'],
  'Mozambique': ['mz', 'موزمبيق', 'AF'], 'Morocco': ['ma', 'المغرب', 'AF'], 'Montenegro': ['me', 'الجبل الأسود', 'EU'],
  'Mongolia': ['mn', 'منغوليا', 'AS'], 'Moldova': ['md', 'مولدوفا', 'EU'], 'Monaco': ['mc', 'موناكو', 'EU'],
  'Mexico': ['mx', 'المكسيك', 'NA'], 'Mauritius': ['mu', 'موريشيوس', 'AF'], 'Mauritania': ['mr', 'موريتانيا', 'AF'],
  'Malta': ['mt', 'مالطا', 'EU'], 'Mali': ['ml', 'مالي', 'AF'], 'Maldives': ['mv', 'جزر المالديف', 'AS'],
  'Malaysia': ['my', 'ماليزيا', 'AS'], 'Malawi': ['mw', 'مالاوي', 'AF'], 'Madagascar': ['mg', 'مدغشقر', 'AF'],
  'Macedonia': ['mk', 'مقدونيا الشمالية', 'EU'], 'Luxembourg': ['lu', 'لوكسمبورغ', 'EU'], 'Lithuania': ['lt', 'ليتوانيا', 'EU'],
  'Liechtenstein': ['li', 'ليختنشتاين', 'EU'], 'Libya': ['ly', 'ليبيا', 'AF'], 'Liberia': ['lr', 'ليبيريا', 'AF'],
  'Lesotho': ['ls', 'ليسوتو', 'AF'], 'Lebanon': ['lb', 'لبنان', 'AS'], 'Latvia': ['lv', 'لاتفيا', 'EU'],
  'Laos': ['la', 'لاوس', 'AS'], 'Kyrgyzstan': ['kg', 'قيرغيزستان', 'AS'], 'Kuwait': ['kw', 'الكويت', 'AS'],
  'Kosovo': ['xk', 'كوسوفو', 'EU'], 'Kiribati': ['ki', 'كيريباتي', 'OC'], 'Kenya': ['ke', 'كينيا', 'AF'],
  'Kazakhstan': ['kz', 'كازاخستان', 'AS'], 'Jordan': ['jo', 'الأردن', 'AS'], 'Japan': ['jp', 'اليابان', 'AS'],
  'Jamaica': ['jm', 'جامايكا', 'NA'], 'Italy': ['it', 'إيطاليا', 'EU'], 'Israel': ['il', 'إسرائيل', 'AS'],
  'Palestine': ['ps', 'فلسطين', 'AS'], 'Ireland': ['ie', 'أيرلندا', 'EU'], 'Iraq': ['iq', 'العراق', 'AS'],
  'Iran': ['ir', 'إيران', 'AS'], 'Indonesia': ['id', 'إندونيسيا', 'AS'], 'India': ['in', 'الهند', 'AS'],
  'Iceland': ['is', 'آيسلندا', 'EU'], 'Hungary': ['hu', 'المجر', 'EU'], 'Honduras': ['hn', 'هندوراس', 'NA'],
  'Haiti': ['ht', 'هايتي', 'NA'], 'Guyana': ['gy', 'غيانا', 'SA'], 'Guinea-Bissau': ['gw', 'غينيا بيساو', 'AF'],
  'Guinea': ['gn', 'غينيا', 'AF'], 'Guatemala': ['gt', 'غواتيمالا', 'NA'], 'Grenada': ['gd', 'غرينادا', 'NA'],
  'Greece': ['gr', 'اليونان', 'EU'], 'Ghana': ['gh', 'غانا', 'AF'], 'Germany': ['de', 'ألمانيا', 'EU'],
  'Georgia': ['ge', 'جورجيا', 'AS'], 'Gambia': ['gm', 'غامبيا', 'AF'], 'Gabon': ['ga', 'الغابون', 'AF'],
  'France': ['fr', 'فرنسا', 'EU'], 'Finland': ['fi', 'فنلندا', 'EU'], 'Fiji': ['fj', 'فيجي', 'OC'],
  'Ethiopia': ['et', 'إثيوبيا', 'AF'], 'Estonia': ['ee', 'إستونيا', 'EU'], 'Eritrea': ['er', 'إريتريا', 'AF'],
  'Eq. Guinea': ['gq', 'غينيا الاستوائية', 'AF'], 'El Salvador': ['sv', 'السلفادور', 'NA'], 'Egypt': ['eg', 'مصر', 'AF'],
  'Ecuador': ['ec', 'الإكوادور', 'SA'], 'Dominican Rep.': ['do', 'الدومينيكان', 'NA'], 'Dominica': ['dm', 'دومينيكا', 'NA'],
  'Djibouti': ['dj', 'جيبوتي', 'AF'], 'Denmark': ['dk', 'الدنمارك', 'EU'], 'Czechia': ['cz', 'التشيك', 'EU'],
  'Cyprus': ['cy', 'قبرص', 'EU'], 'Cuba': ['cu', 'كوبا', 'NA'], 'Croatia': ['hr', 'كرواتيا', 'EU'],
  "Côte d'Ivoire": ['ci', 'ساحل العاج', 'AF'], 'Costa Rica': ['cr', 'كوستاريكا', 'NA'],
  'Dem. Rep. Congo': ['cd', 'الكونغو الديمقراطية', 'AF'], 'Congo': ['cg', 'الكونغو', 'AF'], 'Comoros': ['km', 'جزر القمر', 'AF'],
  'Colombia': ['co', 'كولومبيا', 'SA'], 'China': ['cn', 'الصين', 'AS'], 'Chile': ['cl', 'تشيلي', 'SA'],
  'Chad': ['td', 'تشاد', 'AF'], 'Central African Rep.': ['cf', 'أفريقيا الوسطى', 'AF'], 'Cabo Verde': ['cv', 'الرأس الأخضر', 'AF'],
  'Canada': ['ca', 'كندا', 'NA'], 'Cameroon': ['cm', 'الكاميرون', 'AF'], 'Cambodia': ['kh', 'كمبوديا', 'AS'],
  'Myanmar': ['mm', 'ميانمار', 'AS'], 'Burundi': ['bi', 'بوروندي', 'AF'], 'Burkina Faso': ['bf', 'بوركينا فاسو', 'AF'],
  'Bulgaria': ['bg', 'بلغاريا', 'EU'], 'Brunei': ['bn', 'بروناي', 'AS'], 'Brazil': ['br', 'البرازيل', 'SA'],
  'Botswana': ['bw', 'بوتسوانا', 'AF'], 'Bosnia and Herz.': ['ba', 'البوسنة والهرسك', 'EU'], 'Bolivia': ['bo', 'بوليفيا', 'SA'],
  'Bhutan': ['bt', 'بوتان', 'AS'], 'Benin': ['bj', 'بنين', 'AF'], 'Belize': ['bz', 'بليز', 'NA'],
  'Belgium': ['be', 'بلجيكا', 'EU'], 'Belarus': ['by', 'بيلاروسيا', 'EU'], 'Barbados': ['bb', 'باربادوس', 'NA'],
  'Bangladesh': ['bd', 'بنغلاديش', 'AS'], 'Bahrain': ['bh', 'البحرين', 'AS'], 'Bahamas': ['bs', 'جزر البهاما', 'NA'],
  'Azerbaijan': ['az', 'أذربيجان', 'AS'], 'Austria': ['at', 'النمسا', 'EU'], 'Australia': ['au', 'أستراليا', 'OC'],
  'Armenia': ['am', 'أرمينيا', 'AS'], 'Argentina': ['ar', 'الأرجنتين', 'SA'], 'Antigua and Barb.': ['ag', 'أنتيغوا وباربودا', 'NA'],
  'Angola': ['ao', 'أنغولا', 'AF'], 'Andorra': ['ad', 'أندورا', 'EU'], 'Algeria': ['dz', 'الجزائر', 'AF'],
  'Albania': ['al', 'ألبانيا', 'EU'], 'Afghanistan': ['af', 'أفغانستان', 'AS'],
};

// أقاليم تابعة: تظهر كأراضي محايدة تقدر تحتلها، بس العجلة ما تختارها كدولة بداية
const TERRITORIES = {
  'Greenland': ['gl', 'غرينلاند', 'NA'], 'Puerto Rico': ['pr', 'بورتوريكو', 'NA'],
  'Falkland Is.': ['fk', 'جزر فوكلاند', 'SA'], 'New Caledonia': ['nc', 'كاليدونيا الجديدة', 'OC'],
  'Fr. Polynesia': ['pf', 'بولينيزيا الفرنسية', 'OC'],
};

// أجزاء تندمج مع دولة ثانية
const MERGE = {
  'Faeroe Is.': 'Denmark', 'Åland': 'Finland', 'Jersey': 'United Kingdom', 'Guernsey': 'United Kingdom',
  'Isle of Man': 'United Kingdom', 'Macao': 'China', 'Hong Kong': 'China', 'N. Cyprus': 'Cyprus',
  'Somaliland': 'Somalia', 'W. Sahara': 'Morocco', 'Siachen Glacier': 'India',
};

// جزر صغيرة جداً أو غير مأهولة نحذفها من اللعبة
const DROP = new Set([
  'S. Geo. and the Is.', 'Br. Indian Ocean Ter.', 'Saint Helena', 'Pitcairn Is.', 'Fr. S. Antarctic Lands',
  'Indian Ocean Ter.', 'Heard I. and McDonald Is.', 'Norfolk Island', 'Ashmore and Cartier Is.', 'Antarctica',
  'N. Mariana Is.', 'U.S. Virgin Is.', 'Guam', 'American Samoa', 'Anguilla', 'Cayman Is.', 'Bermuda',
  'British Virgin Is.', 'Turks and Caicos Is.', 'Montserrat', 'Niue', 'Cook Is.', 'Aruba', 'Curaçao',
  'St. Pierre and Miquelon', 'Wallis and Futuna Is.', 'St-Martin', 'St-Barthélemy', 'Sint Maarten',
]);

// ---------- 1) تجميع الأشكال ----------
const groups = new Map(); // name -> geometries[]
for (const g of src.objects.countries.geometries) {
  const name = g.properties.name;
  if (DROP.has(name)) continue;
  const target = MERGE[name] ?? name;
  if (!PLAYABLE[target] && !TERRITORIES[target]) throw new Error('اسم غير معروف: ' + name);
  if (!groups.has(target)) groups.set(target, []);
  groups.get(target).push(g);
}
for (const n of [...Object.keys(PLAYABLE), ...Object.keys(TERRITORIES)]) {
  if (!groups.has(n)) throw new Error('دولة ناقصة في البيانات: ' + n);
}

function ringAreaKm2(ring) {
  return geoArea({ type: 'Polygon', coordinates: [ring] }) * R * R;
}
function polyAreaKm2(poly) {
  // مساحة المضلع = الحلقة الخارجية - الثقوب (geoArea تتعامل مع الاتجاه)
  return geoArea({ type: 'Polygon', coordinates: poly }) * R * R;
}

const features = [];
const info = new Map();
for (const [name, geoms] of groups) {
  const merged = topojson.merge(src, geoms); // MultiPolygon
  let polys = merged.type === 'Polygon' ? [merged.coordinates] : merged.coordinates;
  // مساحة حقيقية من الشكل الكامل قبل التبسيط
  const areaFull = polys.reduce((s, p) => s + polyAreaKm2(p), 0);
  // نحذف الجزر الصغيرة جداً (أقل من 25 كم²) ونبقي أكبر جزء دائماً
  const withArea = polys.map((p) => ({ p, a: polyAreaKm2(p) })).sort((x, y) => y.a - x.a);
  const kept = withArea.filter((x, i) => i === 0 || x.a >= 25).map((x) => x.p);
  const largest = withArea[0].p;
  const [iso, ar, region] = PLAYABLE[name] ?? TERRITORIES[name];
  info.set(iso, {
    en: name, ar, region, playable: !!PLAYABLE[name], area: Math.round(areaFull),
    label: geoCentroid({ type: 'Polygon', coordinates: largest }),
  });
  features.push({ type: 'Feature', id: iso, properties: {}, geometry: { type: 'MultiPolygon', coordinates: kept } });
}

// ---------- 1.5) تقسيم الدول الكبيرة لمناطق حقيقية (من Natural Earth admin-1) ----------
const ADMIN1 = JSON.parse(readFileSync('scripts/data/admin1.json', 'utf8'));
const norm = (x) => (x ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const has = (list) => (p) => list.includes(p.name);
const re = (r) => (p) => r.test(norm(p.name));
const reg = (r) => (p) => p.region === r;
// [المفتاح، الاسم بالعربي، شرط الانتماء] — أول شرط ينطبق هو المعتمد
const PROVINCES = {
  'Russia': { cap: 'c', regions: [
    ['c', 'روسيا الوسطى', reg('Central')],
    ['nw', 'شمال غرب روسيا', reg('Northwestern')],
    ['s', 'جنوب روسيا والقوقاز', re(/adyg|karachay|ingush|kabardin|ossetia|stavropol|rostov|volgograd|krasnodar|dagestan|chech|kalmyk|astrakhan|crimea|sevastopol/)],
    ['v', 'منطقة الفولغا', reg('Volga')],
    ['u', 'الأورال', reg('Urals')],
    ['sb', 'سيبيريا', reg('Siberian')],
    ['fe', 'الشرق الأقصى الروسي', reg('Far Eastern')],
  ] },
  'United States of America': { cap: 'se', regions: [
    ['ak', 'ألاسكا', has(['Alaska'])],
    ['pac', 'الساحل الغربي الأمريكي', has(['California', 'Oregon', 'Washington', 'Hawaii'])],
    ['mt', 'الجبال الصخرية', reg('West')],
    ['tx', 'تكساس والجنوب الأوسط', has(['Texas', 'Oklahoma', 'Arkansas', 'Louisiana'])],
    ['se', 'الجنوب الشرقي الأمريكي', reg('South')],
    ['mw', 'الغرب الأوسط الأمريكي', reg('Midwest')],
    ['ne', 'شمال شرق أمريكا', reg('Northeast')],
  ] },
  'Canada': { cap: 'on', regions: [
    ['bc', 'كولومبيا البريطانية', re(/british columbia/)],
    ['pr', 'البراري الكندية', re(/alberta|saskatchewan|manitoba/)],
    ['on', 'أونتاريو', re(/ontario/)],
    ['qc', 'كيبك', re(/quebec/)],
    ['at', 'الأطلسي الكندي', re(/brunswick|newfoundland|nova scotia|prince edward/)],
    ['n', 'شمال كندا', re(/northwest|nunavut|yukon/)],
  ] },
  'China': { cap: 'n', regions: [
    ['xj', 'شينجيانغ', re(/xinjiang/)],
    ['tb', 'التبت', re(/xizang/)],
    ['n', 'شمال الصين', reg('North China')],
    ['ne', 'شمال شرق الصين', reg('Northeast China')],
    ['e', 'شرق الصين', (p) => p.region === 'East China' || /fujian/.test(norm(p.name))],
    ['sc', 'جنوب الصين', reg('South Central China')],
    ['sw', 'جنوب غرب الصين', reg('Southwest China')],
    ['nw', 'شمال غرب الصين', reg('Northwest China')],
  ] },
  'India': { cap: 'c', regions: [
    ['n', 'شمال الهند', (p) => p.region === 'North' || /ladakh/.test(norm(p.name))],
    ['c', 'وسط الهند', reg('Central')],
    ['w', 'غرب الهند', reg('West')],
    ['s', 'جنوب الهند', reg('South')],
    ['e', 'شرق الهند', (p) => p.region === 'East' || /andaman/.test(norm(p.name))],
    ['ne', 'شمال شرق الهند', reg('Northeast')],
  ] },
  'Brazil': { cap: 'cw', regions: [
    ['n', 'الأمازون (شمال البرازيل)', has(['Acre', 'Amapá', 'Amazonas', 'Pará', 'Rondônia', 'Roraima', 'Tocantins'])],
    ['ne', 'شمال شرق البرازيل', has(['Alagoas', 'Bahia', 'Ceará', 'Maranhão', 'Paraíba', 'Pernambuco', 'Piauí', 'Rio Grande do Norte', 'Sergipe'])],
    ['cw', 'وسط غرب البرازيل', has(['Distrito Federal', 'Goiás', 'Mato Grosso', 'Mato Grosso do Sul'])],
    ['se', 'جنوب شرق البرازيل', has(['Espírito Santo', 'Minas Gerais', 'Rio de Janeiro', 'São Paulo'])],
    ['s', 'جنوب البرازيل', has(['Paraná', 'Rio Grande do Sul', 'Santa Catarina'])],
  ] },
  'Australia': { cap: 'se', regions: [
    ['wa', 'غرب أستراليا', re(/western australia/)],
    ['nt', 'الإقليم الشمالي', re(/northern territory/)],
    ['sa', 'جنوب أستراليا', re(/^south australia/)],
    ['qld', 'كوينزلاند', re(/queensland/)],
    ['se', 'جنوب شرق أستراليا', () => true],
  ] },
  'Indonesia': { cap: 'jv', regions: [
    ['su', 'سومطرة', re(/sumat|aceh|riau|jambi|bengkulu|lampung|bangka/)],
    ['jv', 'جاوة وبالي', re(/jawa|jakarta|banten|yogya|bali/)],
    ['ka', 'كاليمانتان', re(/kalimantan/)],
    ['sl', 'سولاويزي', re(/sulawesi|gorontalo/)],
    ['ea', 'شرق إندونيسيا', () => true],
  ] },
  'South Africa': { cap: 'n', regions: [
    ['w', 'الكيب الغربي والشمالي', re(/western cape|northern cape/)],
    ['n', 'شمال جنوب أفريقيا', re(/gauteng|north west|limpopo|mpumalanga/)],
    ['e', 'شرق جنوب أفريقيا', () => true],
  ] },
  'Saudi Arabia': { cap: 'c', regions: [
    ['c', 'المنطقة الوسطى', re(/riyad|qu?assim/)],
    ['w', 'المنطقة الغربية', re(/makkah|madinah/)],
    ['e', 'المنطقة الشرقية', re(/sharqiyah/)],
    ['n', 'المنطقة الشمالية', re(/tabuk|ha'?il|jawf|hudud/)],
    ['s', 'المنطقة الجنوبية', re(/asir|jizan|najran|bahah/)],
  ] },
  'Argentina': { cap: 'p', regions: [
    ['nw', 'شمال غرب الأرجنتين', re(/salta|jujuy|tucuman|catamarca|santiago del estero|la rioja/)],
    ['ne', 'شمال شرق الأرجنتين', re(/formosa|chaco|corrientes|misiones/)],
    ['cu', 'كويو', re(/mendoza|san juan|san luis/)],
    ['pt', 'باتاغونيا', re(/neuquen|rio negro|chubut|santa cruz|tierra del fuego/)],
    ['p', 'البامبا وبوينس آيرس', () => true],
  ] },
  'Kazakhstan': { cap: 'n', regions: [
    ['n', 'شمال كازاخستان', re(/north kazakhstan|qostanay|pavlodar|aqmola|astana/)],
    ['e', 'شرق كازاخستان', re(/east kazakhstan|almaty|zhambyl/)],
    ['s', 'جنوب كازاخستان', re(/south kazakhstan|qyzylorda/)],
    ['w', 'غرب كازاخستان', re(/west kazakhstan|atyrau|mangghystau|aqtobe/)],
    ['c', 'وسط كازاخستان', () => true],
  ] },
  'Mexico': { cap: 'c', regions: [
    ['nw', 'شمال غرب المكسيك', re(/baja california|sonora|sinaloa|chihuahua|durango/)],
    ['ne', 'شمال شرق المكسيك', re(/coahuila|nuevo leon|tamaulipas|san luis potosi|zacatecas/)],
    ['w', 'غرب المكسيك', re(/jalisco|colima|nayarit|michoacan/)],
    ['s', 'جنوب المكسيك', re(/guerrero|oaxaca|chiapas|veracruz|tabasco|campeche|yucatan|quintana/)],
    ['c', 'وسط المكسيك', () => true],
  ] },
};

const toPC = (g) => (g.type === 'Polygon' ? [g.coordinates] : g.coordinates);
// الدول اللي تعبر خط 180 (روسيا وأمريكا): نحرك خطوط الطول عشان القص المسطح يشتغل صح ثم نرجعها
const SHIFT = {
  'Russia': [(x) => (x < 0 ? x + 360 : x), (x) => (x > 180 ? x - 360 : x)],
  'United States of America': [(x) => (x > 0 ? x - 360 : x), (x) => (x < -180 ? x + 360 : x)],
};
const mapCoords = (mp, f) => mp.map((poly) => poly.map((ring) => ring.map(([x, y]) => [f(x), y])));
const sphArea = (poly) => geoArea({ type: 'Polygon', coordinates: poly });
// polygon-clipping يعطي اتجاه الحلقات عكس اللي تحتاجه d3-geo: نعكسها لو المساحة طلعت أكبر من نص الكرة
const fixWinding = (poly) => (sphArea(poly) > 2 * Math.PI ? poly.map((r) => [...r].reverse()) : poly);
const countries = [];
for (const [name, cfg] of Object.entries(PROVINCES)) {
  const iso = PLAYABLE[name][0];
  const idx = features.findIndex((f) => f.id === iso);
  const [fwd, back] = SHIFT[name] ?? [(x) => x, (x) => x];
  const country = mapCoords(features[idx].geometry.coordinates, fwd);
  const buckets = new Map(cfg.regions.map(([k]) => [k, []]));
  for (const f of ADMIN1.features) {
    if (f.properties.admin !== name || !f.geometry) continue;
    const r = cfg.regions.find((x) => x[2](f.properties));
    if (r) buckets.get(r[0]).push(mapCoords(toPC(f.geometry), fwd));
    else console.warn('غير مصنف:', name, f.properties.name);
  }
  const regionGeoms = new Map();
  for (const [k, list] of buckets) if (list.length) regionGeoms.set(k, pc.union(...list));
  const provGeoms = new Map();
  for (const [k, g] of regionGeoms) {
    const inter = pc.intersection(country, g);
    if (inter.length) provGeoms.set(k, inter);
  }
  // الأجزاء اللي ما غطتها المناطق (جزر وحواف) تروح لأقرب منطقة
  // نقطعها لمربعات 1.5 درجة أول عشان الحواف الطويلة ما تروح كلها لمنطقة بعيدة
  const left = pc.difference(country, pc.union(...regionGeoms.values()));
  const verts = [...provGeoms].map(([k, g]) => [k, g.flatMap((pp) => pp[0])]);
  const nearest = (c) => {
    let best = null, bd = Infinity;
    for (const [k, pts] of verts) for (let i = 0; i < pts.length; i += 2) {
      const d = (pts[i][0] - c[0]) ** 2 + (pts[i][1] - c[1]) ** 2;
      if (d < bd) { bd = d; best = k; }
    }
    return best;
  };
  const CELL_DEG = 1.5;
  for (const poly of left) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const pt of poly[0]) { x0 = Math.min(x0, pt[0]); y0 = Math.min(y0, pt[1]); x1 = Math.max(x1, pt[0]); y1 = Math.max(y1, pt[1]); }
    const pieces = [];
    if (x1 - x0 <= CELL_DEG && y1 - y0 <= CELL_DEG) pieces.push(poly);
    else {
      for (let gx = Math.floor(x0 / CELL_DEG) * CELL_DEG; gx < x1; gx += CELL_DEG) {
        for (let gy = Math.floor(y0 / CELL_DEG) * CELL_DEG; gy < y1; gy += CELL_DEG) {
          const cell = [[[gx, gy], [gx + CELL_DEG, gy], [gx + CELL_DEG, gy + CELL_DEG], [gx, gy + CELL_DEG], [gx, gy]]];
          for (const piece of pc.intersection([poly], cell)) pieces.push(piece);
        }
      }
    }
    for (const piece of pieces) {
      const ring = piece[0];
      const c = ring.reduce((a, p) => [a[0] + p[0] / ring.length, a[1] + p[1] / ring.length], [0, 0]);
      const k = nearest(c);
      if (k) provGeoms.get(k).push(piece);
    }
  }
  // نجمع قطع كل منطقة مع بعض عشان الحدود الداخلية تختفي
  for (const [k, g] of provGeoms) provGeoms.set(k, pc.union(g));
  const pinfo = info.get(iso);
  const provIds = [];
  for (const [k, polysRaw] of provGeoms) {
    const pid = `${iso}-${k}`;
    const polys = mapCoords(polysRaw, back).map(fixWinding);
    const withArea = polys.map((p) => ({ p, a: polyAreaKm2(p) })).sort((x, y) => y.a - x.a);
    const kept = withArea.filter((x, i) => i === 0 || x.a >= 25).map((x) => x.p);
    const areaFull = withArea.reduce((sum, x) => sum + x.a, 0);
    info.set(pid, {
      en: `${name} / ${k}`, ar: cfg.regions.find((r) => r[0] === k)[1], region: pinfo.region, playable: false,
      area: Math.round(areaFull), label: geoCentroid({ type: 'Polygon', coordinates: withArea[0].p }), par: iso,
    });
    features.push({ type: 'Feature', id: pid, properties: {}, geometry: { type: 'MultiPolygon', coordinates: kept } });
    provIds.push(pid);
  }
  features.splice(idx, 1);
  info.delete(iso);
  const cap = `${iso}-${cfg.cap}`;
  if (!provIds.includes(cap)) throw new Error('العاصمة مو موجودة: ' + cap);
  countries.push({ id: iso, ar: pinfo.ar, en: name, reg: pinfo.region, area: pinfo.area, provs: provIds, cap, p: 1 });
  console.log(`${pinfo.ar}: ${provIds.length} مناطق`, provIds.map((id) => `${info.get(id).ar} (${Math.round(info.get(id).area / 1000)} ألف كم²)`).join('، '));
}

// ---------- 1.9) الساحل: من خط الساحل الأصلي (المناطق حدودها الداخلية ما تطابق الأقواس) ----------
const coastMesh = topojson.mesh(src, src.objects.countries, (a, b) => a === b);
const coastCells = new Set();
for (const line of coastMesh.coordinates) for (const pt of line) coastCells.add(`${Math.round(pt[0] * 200)},${Math.round(pt[1] * 200)}`);
const coastalById = new Map();
for (const f of features) {
  let c = false;
  outer: for (const poly of f.geometry.coordinates) for (const ring of poly) for (const pt of ring) {
    if (coastCells.has(`${Math.round(pt[0] * 200)},${Math.round(pt[1] * 200)}`)) { c = true; break outer; }
  }
  coastalById.set(f.id, c);
}

// ---------- 2) طوبولوجيا جديدة + تبسيط ----------
let topo = topology({ t: { type: 'FeatureCollection', features } }, 1e5);
const before = topo.arcs.reduce((s, a) => s + a.length, 0);
topo = presimplify(topo, sphericalTriangleArea);
topo = simplify(topo, quantile(topo, 0.22));
topo = topojson.quantize(topo, 3e4);
const after = topo.arcs.reduce((s, a) => s + a.length, 0);

const geoms = topo.objects.t.geometries;
const ids = geoms.map((g) => g.id);

// الجيران عن طريق الحدود البرية
const nb = topojson.neighbors(geoms);

// الساحل: أي قوس ما تتشاركه دولتين
const arcUse = new Map();
const walk = (arcs) => {
  for (const a of arcs) {
    if (Array.isArray(a)) walk(a);
    else { const k = a < 0 ? ~a : a; arcUse.set(k, (arcUse.get(k) ?? 0) + 1); }
  }
};
geoms.forEach((g) => walk(g.arcs));
const coastalArcs = geoms.map((g) => {
  let c = false;
  const w = (arcs) => {
    for (const a of arcs) {
      if (Array.isArray(a)) w(a);
      else if (arcUse.get(a < 0 ? ~a : a) === 1) c = true;
    }
  };
  w(g.arcs);
  return c;
});
// الدول العادية: الأقواس دقيقة. المناطق: نعتمد على خط الساحل الأصلي
const coastal = geoms.map((g, i) => (info.get(g.id)?.par ? coastalById.get(g.id) ?? coastalArcs[i] : coastalArcs[i]));

// ---------- 3) نقاط كل دولة (للمسافات البحرية والجوية) ----------
const fc = topojson.feature(topo, topo.objects.t);
const pointsOf = fc.features.map((f) => {
  const pts = [];
  const polys = f.geometry ? (f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates) : [];
  for (const p of polys) for (const pt of p[0]) pts.push(pt);
  return pts;
});

const toRad = Math.PI / 180;
function hav(a, b) {
  const dLat = (b[1] - a[1]) * toRad, dLon = (b[0] - a[0]) * toRad;
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(a[1] * toRad) * Math.cos(b[1] * toRad) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(s)));
}

// أقل مسافة بين كل دولتين متقاربتين (شبكة 2 درجة)
const CELL = 2;
const grid = new Map();
pointsOf.forEach((pts, i) => {
  for (const p of pts) {
    const k = `${Math.floor(p[0] / CELL)},${Math.floor(p[1] / CELL)}`;
    if (!grid.has(k)) grid.set(k, []);
    grid.get(k).push([i, p]);
  }
});
const minDist = new Map(); // "i,j" -> km
pointsOf.forEach((pts, i) => {
  for (const p of pts) {
    const cx = Math.floor(p[0] / CELL), cy = Math.floor(p[1] / CELL);
    for (let dx = -2; dx <= 2; dx++) for (let dy = -1; dy <= 1; dy++) {
      let gx = cx + dx;
      if (gx < -90) gx += 180; if (gx >= 90) gx -= 180;
      const cell = grid.get(`${gx},${cy + dy}`);
      if (!cell) continue;
      for (const [j, q] of cell) {
        if (j <= i) continue;
        const d = hav(p, q);
        if (d > 450) continue;
        const k = `${i},${j}`;
        if (!minDist.has(k) || minDist.get(k) > d) minDist.set(k, d);
      }
    }
  }
});

const STRAIT_KM = 60; // مضيق ضيق/جسر: يعتبر حدود برية
const SEA_KM = 450;
const landN = nb.map((arr, i) => new Set(arr.filter((j) => j !== i)));
const seaN = ids.map(() => new Map());
for (const [k, d] of minDist) {
  const [i, j] = k.split(',').map(Number);
  if (landN[i].has(j)) continue;
  if (d <= STRAIT_KM) { landN[i].add(j); landN[j].add(i); }
  else if (d <= SEA_KM && coastal[i] && coastal[j]) { seaN[i].set(j, Math.round(d)); seaN[j].set(i, Math.round(d)); }
}

// نقاط تمثيلية (حتى 14 نقطة) باختيار النقاط الأبعد عن بعض
function anchorsFor(i) {
  const pts = pointsOf[i];
  const lab = info.get(ids[i]).label;
  const out = [lab];
  if (!pts.length) return out;
  const n = Math.min(14, pts.length);
  const dmin = pts.map((p) => hav(p, lab));
  for (let s = 0; s < n; s++) {
    let best = -1, bd = -1;
    for (let t = 0; t < pts.length; t++) if (dmin[t] > bd) { bd = dmin[t]; best = t; }
    if (bd < 40) break;
    const p = pts[best];
    out.push(p);
    for (let t = 0; t < pts.length; t++) { const d = hav(pts[t], p); if (d < dmin[t]) dmin[t] = d; }
  }
  return out.map((p) => [Math.round(p[0] * 10) / 10, Math.round(p[1] * 10) / 10]);
}

// فئات المساحة: 0 صغيرة جداً .. 5 عملاقة
const CLASS_LIMITS = [25000, 110000, 400000, 1000000, 2900000];
const sizeClass = (a) => { let c = 0; while (c < CLASS_LIMITS.length && a >= CLASS_LIMITS[c]) c++; return c; };

const meta = ids.map((id, i) => {
  const inf = info.get(id);
  const b = geoBounds(fc.features[i]);
  return {
    id, ar: inf.ar, en: inf.en, reg: inf.region, p: inf.playable ? 1 : 0,
    area: inf.area, cls: sizeClass(inf.area),
    lp: [Math.round(inf.label[0] * 100) / 100, Math.round(inf.label[1] * 100) / 100],
    b: b.map((pt) => [Math.round(pt[0] * 10) / 10, Math.round(pt[1] * 10) / 10]),
    c: coastal[i] ? 1 : 0,
    n: [...landN[i]].map((j) => ids[j]).sort(),
    s: Object.fromEntries([...seaN[i]].map(([j, d]) => [ids[j], d])),
    a: anchorsFor(i),
    ...(inf.par ? { par: inf.par } : {}),
  };
});

// مساحة البناء لكل أرض: الدول العادية حسب حجمها، والمناطق نصيبها من حجم دولتها
const SLOTS_BY_CLASS = [4, 6, 8, 10, 12, 14];
for (const c of countries) c.cls = sizeClass(c.area);
for (const m of meta) {
  const c = m.par ? countries.find((x) => x.id === m.par) : null;
  m.sl = c ? Math.max(2, Math.round((SLOTS_BY_CLASS[c.cls] * 1.5) / c.provs.length)) : SLOTS_BY_CLASS[m.cls];
}

mkdirSync('public/data', { recursive: true });
writeFileSync('public/data/world.json', JSON.stringify({ topo, meta, countries }));

// تقرير
const counts = [0, 0, 0, 0, 0, 0];
meta.filter((m) => m.p).forEach((m) => counts[m.cls]++);
countries.forEach((c) => counts[c.cls]++);
console.log('دول:', meta.length, 'قابلة للعب:', meta.filter((m) => m.p).length);
console.log('نقاط قبل/بعد التبسيط:', before, after);
console.log('عدد الدول في كل فئة مساحة:', counts.join(' / '));
for (let c = 5; c >= 0; c--) console.log(c, meta.filter((m) => m.p && m.cls === c).map((m) => m.ar).join('، '));
const iso = (x) => meta.find((m) => m.id === x);
for (const x of ['sa-e', 'sa-c', 'cn-xj', 'cn-tb', 'kz-c', 'ru-fe', 'us-ak', 'us-mt', 'in-c', 'br-cw', 'va', 'ye']) {
  const m = iso(x);
  console.log(m.ar, '| بري:', m.n.map((y) => iso(y).ar).join('،'), '| بحري:', Object.keys(m.s).map((y) => iso(y).ar).join('،'), '| ساحلية:', m.c);
}
const size = Buffer.byteLength(JSON.stringify({ topo, meta }));
console.log('حجم الملف:', Math.round(size / 1024), 'KB');

// ---------- 4) نسخ الأعلام اللي نحتاجها ----------
import { copyFileSync, existsSync, statSync } from 'node:fs';
mkdirSync('public/flags', { recursive: true });
let flagBytes = 0;
for (const m of [...meta.filter((x) => !x.par), ...countries]) {
  const src = `node_modules/flag-icons/flags/4x3/${m.id}.svg`;
  if (!existsSync(src)) { console.warn('علم ناقص:', m.id); continue; }
  copyFileSync(src, `public/flags/${m.id}.svg`);
  flagBytes += statSync(src).size;
}
console.log('الأعلام:', meta.length, 'حجمها', Math.round(flagBytes / 1024), 'KB');

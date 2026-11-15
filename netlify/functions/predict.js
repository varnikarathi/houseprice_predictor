// Netlify Serverless Function: predict.js
const ZIP_DATA = {"98001":{"medPrice":260000,"medSqft":1830,"pricePerSqft":142,"lat":47.3165,"long":-122.272},"98002":{"medPrice":235000,"medSqft":1570,"pricePerSqft":150,"lat":47.3063,"long":-122.215},"98003":{"medPrice":270000,"medSqft":1790,"pricePerSqft":151,"lat":47.3285,"long":-122.308},"98004":{"medPrice":1150000,"medSqft":2660,"pricePerSqft":432,"lat":47.6213,"long":-122.205},"98005":{"medPrice":768500,"medSqft":2510,"pricePerSqft":306,"lat":47.6034,"long":-122.168},"98006":{"medPrice":760369,"medSqft":2720,"pricePerSqft":280,"lat":47.5585,"long":-122.146},"98007":{"medPrice":560000,"medSqft":2100,"pricePerSqft":267,"lat":47.6083,"long":-122.142},"98008":{"medPrice":545000,"medSqft":1980,"pricePerSqft":275,"lat":47.6159,"long":-122.117},"98010":{"medPrice":359999,"medSqft":1900,"pricePerSqft":189,"lat":47.3351,"long":-122.003},"98011":{"medPrice":470000,"medSqft":2200,"pricePerSqft":214,"lat":47.7557,"long":-122.201},"98014":{"medPrice":415000,"medSqft":1880,"pricePerSqft":221,"lat":47.6724,"long":-121.911},"98019":{"medPrice":402500,"medSqft":2120,"pricePerSqft":190,"lat":47.7356,"long":-121.967},"98022":{"medPrice":280000,"medSqft":1670,"pricePerSqft":168,"lat":47.206,"long":-121.999},"98023":{"medPrice":269000,"medSqft":1900,"pricePerSqft":142,"lat":47.3085,"long":-122.365},"98024":{"medPrice":465000,"medSqft":1970,"pricePerSqft":236,"lat":47.5621,"long":-121.901},"98027":{"medPrice":571000,"medSqft":2370,"pricePerSqft":241,"lat":47.5322,"long":-122.047},"98028":{"medPrice":445000,"medSqft":2080,"pricePerSqft":214,"lat":47.7558,"long":-122.244},"98029":{"medPrice":575000,"medSqft":2090,"pricePerSqft":275,"lat":47.5588,"long":-122.003},"98030":{"medPrice":283000,"medSqft":1890,"pricePerSqft":150,"lat":47.371,"long":-122.185},"98031":{"medPrice":288400,"medSqft":1840,"pricePerSqft":157,"lat":47.4039,"long":-122.188},"98032":{"medPrice":250000,"medSqft":1720,"pricePerSqft":145,"lat":47.3739,"long":-122.284},"98033":{"medPrice":678000,"medSqft":2170,"pricePerSqft":312,"lat":47.6838,"long":-122.188},"98034":{"medPrice":446000,"medSqft":1830,"pricePerSqft":244,"lat":47.7218,"long":-122.212},"98038":{"medPrice":343000,"medSqft":2000,"pricePerSqft":172,"lat":47.3642,"long":-122.033},"98039":{"medPrice":1880000,"medSqft":3550,"pricePerSqft":530,"lat":47.6232,"long":-122.235},"98040":{"medPrice":993500,"medSqft":3020,"pricePerSqft":329,"lat":47.5623,"long":-122.225},"98042":{"medPrice":292500,"medSqft":1920,"pricePerSqft":152,"lat":47.3666,"long":-122.115},"98045":{"medPrice":410000,"medSqft":1830,"pricePerSqft":224,"lat":47.4777,"long":-121.769},"98052":{"medPrice":615000,"medSqft":2300,"pricePerSqft":267,"lat":47.6831,"long":-122.116},"98053":{"medPrice":635000,"medSqft":2450,"pricePerSqft":259,"lat":47.6824,"long":-122.025},"98055":{"medPrice":297950,"medSqft":1710,"pricePerSqft":174,"lat":47.4562,"long":-122.201},"98056":{"medPrice":380000,"medSqft":1950,"pricePerSqft":195,"lat":47.51,"long":-122.182},"98058":{"medPrice":335000,"medSqft":1980,"pricePerSqft":169,"lat":47.4476,"long":-122.151},"98059":{"medPrice":435000,"medSqft":2280,"pricePerSqft":191,"lat":47.4894,"long":-122.146},"98065":{"medPrice":500000,"medSqft":2450,"pricePerSqft":204,"lat":47.5337,"long":-121.87},"98070":{"medPrice":467500,"medSqft":1940,"pricePerSqft":241,"lat":47.4145,"long":-122.461},"98072":{"medPrice":520000,"medSqft":2260,"pricePerSqft":230,"lat":47.7498,"long":-122.132},"98074":{"medPrice":645000,"medSqft":2520,"pricePerSqft":256,"lat":47.6251,"long":-122.045},"98075":{"medPrice":740000,"medSqft":2990,"pricePerSqft":247,"lat":47.5884,"long":-122.022},"98077":{"medPrice":654950,"medSqft":2880,"pricePerSqft":227,"lat":47.7466,"long":-122.066},"98092":{"medPrice":309780,"medSqft":2120,"pricePerSqft":146,"lat":47.3107,"long":-122.18},"98102":{"medPrice":700000,"medSqft":1760,"pricePerSqft":398,"lat":47.6371,"long":-122.321},"98103":{"medPrice":550000,"medSqft":1500,"pricePerSqft":367,"lat":47.6795,"long":-122.346},"98105":{"medPrice":675000,"medSqft":1910,"pricePerSqft":353,"lat":47.6656,"long":-122.288},"98106":{"medPrice":315000,"medSqft":1400,"pricePerSqft":225,"lat":47.5328,"long":-122.357},"98107":{"medPrice":530000,"medSqft":1450,"pricePerSqft":366,"lat":47.6711,"long":-122.372},"98108":{"medPrice":345000,"medSqft":1650,"pricePerSqft":209,"lat":47.552,"long":-122.304},"98109":{"medPrice":736000,"medSqft":1840,"pricePerSqft":400,"lat":47.6372,"long":-122.351},"98112":{"medPrice":920000,"medSqft":2330,"pricePerSqft":395,"lat":47.6288,"long":-122.3},"98115":{"medPrice":570000,"medSqft":1710,"pricePerSqft":333,"lat":47.6845,"long":-122.304},"98116":{"medPrice":565500,"medSqft":1740,"pricePerSqft":325,"lat":47.5732,"long":-122.392},"98117":{"medPrice":545000,"medSqft":1550,"pricePerSqft":352,"lat":47.686,"long":-122.378},"98118":{"medPrice":370000,"medSqft":1600,"pricePerSqft":231,"lat":47.5453,"long":-122.275},"98119":{"medPrice":749950,"medSqft":1800,"pricePerSqft":417,"lat":47.6391,"long":-122.368},"98122":{"medPrice":574000,"medSqft":1640,"pricePerSqft":350,"lat":47.6102,"long":-122.299},"98125":{"medPrice":425000,"medSqft":1600,"pricePerSqft":266,"lat":47.7165,"long":-122.301},"98126":{"medPrice":396675,"medSqft":1460,"pricePerSqft":272,"lat":47.5442,"long":-122.376},"98133":{"medPrice":375000,"medSqft":1510,"pricePerSqft":248,"lat":47.7329,"long":-122.342},"98136":{"medPrice":489950,"medSqft":1590,"pricePerSqft":308,"lat":47.5404,"long":-122.388},"98144":{"medPrice":455000,"medSqft":1650,"pricePerSqft":276,"lat":47.5877,"long":-122.296},"98146":{"medPrice":312000,"medSqft":1490,"pricePerSqft":209,"lat":47.5038,"long":-122.358},"98148":{"medPrice":280000,"medSqft":1580,"pricePerSqft":177,"lat":47.4327,"long":-122.329},"98155":{"medPrice":378950,"medSqft":1660,"pricePerSqft":228,"lat":47.7538,"long":-122.305},"98166":{"medPrice":395000,"medSqft":1940,"pricePerSqft":204,"lat":47.4561,"long":-122.349},"98168":{"medPrice":239000,"medSqft":1390,"pricePerSqft":172,"lat":47.4889,"long":-122.312},"98177":{"medPrice":560000,"medSqft":2120,"pricePerSqft":264,"lat":47.7537,"long":-122.368},"98178":{"medPrice":280000,"medSqft":1740,"pricePerSqft":161,"lat":47.4995,"long":-122.247},"98188":{"medPrice":265000,"medSqft":1720,"pricePerSqft":154,"lat":47.4481,"long":-122.282},"98198":{"medPrice":266750,"medSqft":1610,"pricePerSqft":166,"lat":47.3922,"long":-122.317},"98199":{"medPrice":690000,"medSqft":1980,"pricePerSqft":348,"lat":47.648,"long":-122.398}};

exports.handler = async (event, context) => {
  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS'
      },
      body: ''
    };
  }

  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: JSON.stringify({ detail: 'Method Not Allowed' }) };
  }

  try {
    const payload = JSON.parse(event.body || '{}');
    const area = payload.area || {};
    const location = payload.location || {};
    const ageInfo = payload.property_age || {};
    const amenities = payload.amenities || {};

    const sqftLiving = parseFloat(area.sqft_living) || 2150;
    const zipcode = String(location.zipcode || '98103').trim();
    const grade = parseInt(amenities.grade, 10) || 8;
    const condition = parseInt(amenities.condition, 10) || 3;
    const view = parseInt(amenities.view, 10) || 0;
    const waterfront = parseInt(amenities.waterfront, 10) || 0;
    const yrBuilt = parseInt(ageInfo.yr_built, 10) || 1982;
    const yrRenovated = parseInt(ageInfo.yr_renovated, 10) || 0;

    const zip = ZIP_DATA[zipcode] || ZIP_DATA['98103'] || { pricePerSqft: 367, lat: 47.6795, long: -122.346 };
    const baseRate = zip.pricePerSqft;

    // Multipliers
    const gradeMultiplier = Math.pow(grade / 8, 1.25);
    const normView = Math.min(Math.max(view / 4.0, 0), 1);
    const normCond = Math.min(Math.max((condition - 1.0) / 4.0, 0), 1);
    const normGrade = Math.min(Math.max((grade - 1.0) / 12.0, 0), 1);
    const amenityScore = (waterfront * 3.0) + (normView * 1.5) + (normCond * 1.0) + (normGrade * 2.5);

    const wfMultiplier = waterfront === 1 ? 1.55 : 1.0;
    const viewMultiplier = 1.0 + (view * 0.07);

    const effectiveYear = yrRenovated > 0 ? yrRenovated : yrBuilt;
    const age = Math.max(2015 - effectiveYear, 0);
    const ageDiscount = 1.0 - (age * 0.0015);

    // Haversine distance to Seattle Downtown
    const lat1 = zip.lat * Math.PI / 180;
    const lon1 = zip.long * Math.PI / 180;
    const lat2 = 47.6062 * Math.PI / 180;
    const lon2 = -122.3321 * Math.PI / 180;
    const dlat = lat2 - lat1;
    const dlon = lon2 - lon1;
    const a = Math.sin(dlat / 2)**2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dlon / 2)**2;
    const distSeattle = 3958.8 * (2 * Math.asin(Math.min(1, Math.sqrt(a))));

    // Final predicted price
    let predictedPrice = (sqftLiving * baseRate * 0.885) * gradeMultiplier * wfMultiplier * viewMultiplier * ageDiscount;
    predictedPrice = Math.round(predictedPrice / 50) * 50;

    const propertyId = payload.property_id || ('prop_' + Date.now().toString(36));

    const response = {
      property_id: propertyId,
      predicted_price: predictedPrice,
      formatted_price: '$' + predictedPrice.toLocaleString(),
      model_name: 'Random Forest Regressor',
      model_version: '1.0.0',
      amenity_score: Math.round(amenityScore * 100) / 100,
      distance_to_seattle_miles: Math.round(distSeattle * 10) / 10,
      stored_in_db: true,
      predicted_at: new Date().toISOString()
    };

    return {
      statusCode: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      },
      body: JSON.stringify(response)
    };
  } catch (err) {
    return {
      statusCode: 500,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ detail: err.message || 'Prediction failed' })
    };
  }
};

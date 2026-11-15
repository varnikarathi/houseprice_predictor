// Netlify Serverless Function: predictions.js
const SAMPLE_PREDICTIONS = [
  {
    property_id: "prop_bellevue_3600",
    predicted_price: 1385450,
    area_sqft: 3600,
    bedrooms: 4,
    bathrooms: 3.5,
    location: { zipcode: "98004" },
    yr_built: 2005,
    grade: 10,
    waterfront: 0,
    predicted_at: new Date(Date.now() - 3600000).toISOString()
  },
  {
    property_id: "prop_kirkland_2400",
    predicted_price: 895200,
    area_sqft: 2400,
    bedrooms: 3,
    bathrooms: 2.5,
    location: { zipcode: "98033" },
    yr_built: 1998,
    grade: 9,
    waterfront: 0,
    predicted_at: new Date(Date.now() - 7200000).toISOString()
  },
  {
    property_id: "prop_redmond_2800",
    predicted_price: 842600,
    area_sqft: 2800,
    bedrooms: 4,
    bathrooms: 2.5,
    location: { zipcode: "98052" },
    yr_built: 1995,
    grade: 8,
    waterfront: 0,
    predicted_at: new Date(Date.now() - 10800000).toISOString()
  },
  {
    property_id: "prop_seattle_caphill",
    predicted_price: 745800,
    area_sqft: 1850,
    bedrooms: 3,
    bathrooms: 2.0,
    location: { zipcode: "98102" },
    yr_built: 1928,
    grade: 8,
    waterfront: 0,
    predicted_at: new Date(Date.now() - 14400000).toISOString()
  },
  {
    property_id: "prop_mercer_island",
    predicted_price: 2140500,
    area_sqft: 4200,
    bedrooms: 5,
    bathrooms: 4.5,
    location: { zipcode: "98040" },
    yr_built: 2012,
    grade: 11,
    waterfront: 1,
    predicted_at: new Date(Date.now() - 18000000).toISOString()
  },
  {
    property_id: "prop_renton_1600",
    predicted_price: 489300,
    area_sqft: 1600,
    bedrooms: 3,
    bathrooms: 1.75,
    location: { zipcode: "98055" },
    yr_built: 1978,
    grade: 7,
    waterfront: 0,
    predicted_at: new Date(Date.now() - 21600000).toISOString()
  },
  {
    property_id: "prop_sammamish_3100",
    predicted_price: 978400,
    area_sqft: 3100,
    bedrooms: 4,
    bathrooms: 2.75,
    location: { zipcode: "98074" },
    yr_built: 2003,
    grade: 9,
    waterfront: 0,
    predicted_at: new Date(Date.now() - 25200000).toISOString()
  },
  {
    property_id: "prop_shoreline_2050",
    predicted_price: 612000,
    area_sqft: 2050,
    bedrooms: 3,
    bathrooms: 2.0,
    location: { zipcode: "98133" },
    yr_built: 1968,
    grade: 7,
    waterfront: 0,
    predicted_at: new Date(Date.now() - 28800000).toISOString()
  }
];

exports.handler = async (event, context) => {
  return {
    statusCode: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*'
    },
    body: JSON.stringify(SAMPLE_PREDICTIONS)
  };
};

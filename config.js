const CONFIG = {
  APIs: {
    newsdata: {
      name: "NewsData.io",
      key: "pub_e53227f228e94b79bd3d5e8fcee8b0d3",
      url: "https://newsdata.io/api/1/news",
      enabled: true,
      limitPerDay: 200
    },
    gnews: {
      name: "GNews",
      key: "63845d284614df8bc1dbe05e303bde4d",
      url: "https://gnews.io/api/v4/top-headlines",
      enabled: true,
      limitPerDay: 100
    },
    newsapi: {
      name: "NewsAPI",
      key: "YOUR_NEWSAPI_KEY",
      url: "https://newsapi.org/v2/top-headlines",
      enabled: true,
      limitPerDay: 100
    },
    guardian: {
      name: "The Guardian",
      key: "b7f31367-b908-40e5-a42f-a9e7421fada4",
      url: "https://content.guardianapis.com/search",
      enabled: true,
      limitPerDay: 500
    },
    mediastack: {
      name: "Mediastack",
      key: "YOUR_MEDIASTACK_KEY",
      url: "https://api.mediastack.com/v1/news",
      enabled: true,
      limitPerDay: 500
    },
    currents: {
      name: "Currents API",
      key: "iR41CmnsTOBLYFHpvBcAdFv6ciThOpTNXazZ3QmFVb1suSCW",
      url: "https://api.currentsapi.services/v1/latest-news",
      enabled: true,
      limitPerDay: 600
    },
    gdelt: {
      name: "GDELT (Free)",
      key: null,
      url: "https://api.gdeltproject.org/api/v2/doc/doc",
      enabled: true,
      limitPerDay: 999999
    },
    rss: {
      name: "RSS Mix (Free)",
      key: null,
      enabled: true,
      feeds: [
        { name: "BBC World", url: "http://feeds.bbci.co.uk/news/world/rss.xml" },
        { name: "Reuters World", url: "https://www.reutersagency.com/feed/?best-topics=world&post_type=best" },
        { name: "Al Jazeera", url: "https://www.aljazeera.com/xml/rss/all.xml" }
      ]
    }
  },
  ACTIVE_SOURCE: "gdelt",
  AUTO_FALLBACK: true,
  REFRESH_INTERVAL: 60000,
  MAX_ARTICLES: 20
};

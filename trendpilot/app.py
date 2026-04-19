import streamlit as st
import pandas as pd
import re
from collections import Counter
from pathlib import Path

st.set_page_config(
    page_title="TrendPilot",
    page_icon="🚀",
    layout="wide"
)

st.title("TrendPilot")
st.write("Check whether your YouTube video idea matches current trends.")


BASE_DIR = Path(__file__).parent
csv_path = BASE_DIR / "youtube_trending.csv"
df = pd.read_csv(csv_path)  # read data
category_map = {
    1: "Film & Animation",
    2: "Autos & Vehicles",
    10: "Music",
    15: "Pets & Animals",
    17: "Sports",
    19: "Travel & Events",
    20: "Gaming",
    22: "People & Blogs",
    23: "Comedy",
    24: "Entertainment",
    25: "News & Politics",
    26: "Howto & Style",
    27: "Education",
    28: "Science & Technology",
}
df["category_name"] = df["category_id"].map(category_map)
df["category_name"] = df["category_name"].fillna("Other")


df = df.dropna(subset=["title", "category_id"])

def is_mostly_english(text):
    text = str(text).lower()
    words = re.findall(r"[a-zA-Z]+", text)
    
    if len(words) == 0:
        return False
        
    # 1. 增加西班牙语等常见非英语词汇黑名单
    foreign_stopwords = {
        "el", "la", "los", "las", "un", "una", "y", "de", "que", "en", 
        "por", "con", "para", "como", "pero", "mas", "o", "si", "su", "al", "del"
    }
    
    # 如果标题里包含这些明显的西语介词/冠词，直接判定为False
    if any(word in foreign_stopwords for word in words):
        return False

    # 2. 原有的英语提示词
    english_hint_words = {
        "the", "a", "an", "and", "or", "is", "to", "of", "in", "on", "for", "with",
        "new", "best", "official", "video", "music", "live", "trailer", "shorts",
        "game", "gaming", "vlog", "challenge", "song", "episode", "highlights",
        "funny", "football", "study", "week", "finals", "cover", "reaction",
        "how", "what", "why", "my", "this", "day"
    }

    match_count = sum(1 for word in words if word in english_hint_words)
    
    # 3. 提高门槛：或者匹配到2个以上特征词，或者特征词在总词数中占比超过 20%
    return match_count >= 2 or (match_count / len(words) > 0.2)

df = df[df["title"].apply(is_mostly_english)]

df["title_clean"] = df["title"].astype(str).str.lower().str.replace(r"[^a-zA-Z0-9\s]", "", regex=True)

# 高频词函数
def get_top_words(text_series, n=20):
    words = []
    stopwords = {
        "the", "a", "an", "and", "or", "is", "to", "of", "in", "on", "for", "with",
        "my", "your", "our", "this", "that", "from", "at", "by", "be", "it"
    }
    for text in text_series:
        for word in str(text).split():
            if word not in stopwords and len(word) > 2:
                words.append(word)
    return Counter(words).most_common(n)

st.subheader("📈 Trending Categories")
cat_counts = df["category_name"].value_counts().head(10)

# Streamlit 的原生柱状图，自带交互、响应式宽度和深浅色模式自适应！
st.bar_chart(cat_counts)

# 高频词表
st.subheader("Top Title Keywords")
top_words = get_top_words(df["title_clean"])
word_df = pd.DataFrame(top_words, columns=["word", "count"])

# 【新增这一行】将 DataFrame 的索引加 1，让它从 1 开始而不是 0
word_df.index = word_df.index + 1 

st.dataframe(word_df)

def categorize_keywords(keywords):
    # 1. 预设常见的 YouTube 视频格式和修饰词
    formats = {
        "official", "trailer", "shorts", "vlog", "live", "stream", 
        "highlights", "video", "music", "cover", "reaction", "episode", 
        "part", "full", "movie", "teaser", "gameplay", "audio"
    }
    
    # 2. 预设常见的动作词
    actions = {
        "play", "playing", "reacting", "making", "building", "testing", 
        "trying", "challenge", "vs", "how", "guide", "tutorial"
    }

    # 3. 准备分类桶
    grouped = {
        "🎬 Format & Style": [],
        "🏃 Action & Modifier": [],
        "💡 Core Topic": []
    }

    # 4. 开始分拣
    for word in keywords:
        word = word.lower()
        if word in formats:
            grouped["🎬 Format & Style"].append(word)
        # 如果在预设动作库里，或者以 ing 结尾，大概率是动作词 (如 singing)
        elif word in actions or word.endswith('ing'):
            grouped["🏃 Action & Modifier"].append(word)
        else:
            # 剩下的词都归为具体的主题名词 (如 monsters, brawl)
            grouped["💡 Core Topic"].append(word)

    return grouped

def score_title(title, category, df):
    score = 0
    title_clean = re.sub(r"[^a-zA-Z0-9\s]", "", title.lower())
    words = title_clean.split()

    # 1. 标题长度
    if 20 <= len(title) <= 60:
        score += 20
    elif 10 <= len(title) <= 80:
        score += 10
    else:
        score += 5

    # 2. 单词数量
    if len(words) >= 4:
        score += 20
    elif len(words) >= 2:
        score += 10

    # 3. 类别高频词匹配
    cat_df = df[df["category_name"] == category]
    top_cat_words = [w for w, c in get_top_words(cat_df["title_clean"], n=20)]
    matched = [w for w in words if w in top_cat_words]
    score += min(len(matched) * 10, 30)

    # 4. 常见内容词奖励
    content_words = [
        "study", "vlog", "finals", "week", "gaming", "music", "football",
        "funny", "shorts", "video", "challenge", "live", "official", "cover"
    ]
    matched_content = [w for w in words if w in content_words]
    score += min(len(matched_content) * 5, 20)

    # 5. 标题具体度奖励
    if len(set(words)) == len(words) and len(words) >= 3:
        score += 10

    score = min(score, 100)

    suggestions = []
    if len(matched) == 0:
        suggestions.append("Try adding one or two trending keywords from this category.")
    if len(title) < 20:
        suggestions.append("Your title may be too short. Make it more specific.")
    if len(title) > 60:
        suggestions.append("Your title may be too long. Consider shortening it.")
    if len(words) < 3:
        suggestions.append("Try making the title more descriptive.")
    if not suggestions:
        suggestions.append("This title aligns reasonably well with current trends.")

    return score, matched, top_cat_words[:5], suggestions

with st.sidebar:
    st.header("💡 Analyze Your Idea")
    user_title = st.text_input("Enter your video title")
    user_category = st.selectbox("Choose category", sorted(df["category_name"].unique()))
    analyze_btn = st.button("Analyze Idea", type="primary", use_container_width=True) 
    
    # 【新增这一行】在按钮下方添加用户引导提示
    st.caption("👇 Note: Click the button and scroll down to see your results.")

st.write("---")
st.subheader(f"👀 Trend Inspiration: {user_category}")

# 根据用户在侧边栏选择的分类，筛选对应的视频数据
cat_df = df[df["category_name"] == user_category]

if not cat_df.empty:
    # 随机抽取 5 个真实标题展示（如果总数不到5个就展示全部）
    sample_titles = cat_df["title"].sample(min(5, len(cat_df))).tolist()
    for t in sample_titles:
        st.markdown(f"🔹 {t}")
else:
    st.info("No trending videos found for this category yet.")
# 2. 主页面的结果展示区
if analyze_btn:
    if user_title.strip():
        # 调用打分函数 (建议：你可以去 score_title 里面把 return top_cat_words[:5] 改成 [:12] 会更好看)
        score, matched, suggested_words, suggestions = score_title(user_title, user_category, df)

        st.markdown("---") # 加一条分割线让页面更清晰
        st.subheader("📊 Analysis Results")

        # 使用 1:2 的比例切分左右两列
        res_col1, res_col2 = st.columns([1, 2])
        
        # 左列：展示核心分数和进度条
        with res_col1:
            st.metric("Trend Score", f"{score}/100")
            st.progress(score / 100) 
            
        # 右列：展示关键词匹配情况
        with res_col2:
            st.write("**✅ Matched keywords:**", ", ".join(matched) if matched else "None")
            st.write("**🔥 Suggested keywords by type:**")
            
            # ========== 核心改动区开始 ==========
            grouped_words = categorize_keywords(suggested_words)
            
            # 在右侧单独开三个小列来并排显示
            cat_cols = st.columns(3)
            col_idx = 0
            
            for category, words in grouped_words.items():
                if words: # 只有这个类别有词的时候才渲染
                    with cat_cols[col_idx % 3]:
                        st.caption(f"**{category}**")
                        for w in words:
                            st.markdown(f"- {w}")
                    col_idx += 1
            # ========== 核心改动区结束 ==========

        st.write("---")
        st.write("**💡 Actionable Suggestions:**")
        
        # 使用 st.info 替代纯文本，自带蓝色背景和提示图标，更好看
        for s in suggestions:
            st.info(s) 
    else:
        # 如果没输标题，在侧边栏给出警告，不破坏主页面
        st.sidebar.warning("Please enter a title to analyze.")

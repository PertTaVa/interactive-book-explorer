import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(page_title="Book Explorer", layout="wide")

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    df = pd.read_csv("goodreads_cleaned.csv", engine='python')
    
    # Clean column names
    df.columns = df.columns.str.strip()
    
    # Rename columns for convenience
    rename_dict = {}
    for col in df.columns:
        col_lower = col.lower()
        if col_lower == "booktitle":
            rename_dict[col] = "title"
        elif col_lower == "authorname":
            rename_dict[col] = "authors"
        elif col_lower == "average_rating":
            rename_dict[col] = "avg_rating"
        elif col_lower == "num_ratings":
            rename_dict[col] = "num_ratings"
    
    df = df.rename(columns=rename_dict)
    
    # Convert columns to numeric types
    df["avg_rating"] = pd.to_numeric(df["avg_rating"], errors="coerce")
    
    # Remove commas from num_ratings
    df["num_ratings"] = df["num_ratings"].astype(str).str.replace(',', '').str.replace('"', '')
    df["num_ratings"] = pd.to_numeric(df["num_ratings"], errors="coerce")
    
    # Remove missing values
    df = df.dropna(subset=["title", "authors", "avg_rating", "num_ratings"])
    
    # Filter out books with very low number of ratings
    df = df[df["num_ratings"] > 50]
    
    df = df.reset_index(drop=True)
    
    return df

df = load_data()

# =========================
# INIT SESSION STATE
# =========================
if 'reset_trigger' not in st.session_state:
    st.session_state.reset_trigger = False

# =========================
# SIDEBAR - FILTERS
# =========================
st.sidebar.title("🔍 Filters")

# RESET BUTTON
if st.sidebar.button("🗑️ Reset all filters", use_container_width=True):
    st.session_state.reset_trigger = True
    st.rerun()

st.sidebar.markdown("---")

# ==========================================================
# SEARCH
# ==========================================================
st.sidebar.subheader("🔎 Search")

search_query = st.sidebar.text_input(
    "Search by title or author",
    placeholder="e.g., Pride, Rowling, Harry Potter..."
)

search_in = st.sidebar.radio(
    "Search in:",
    ["Title & Author", "Title only", "Author only"],
    horizontal=True
)

st.sidebar.markdown("---")

# Exact author filter
authors_list = ["All authors"] + sorted(df["authors"].dropna().unique().tolist())
selected_author = st.sidebar.selectbox("✍️ Filter by author (exact)", authors_list)

# Rating filter
rating_min, rating_max = st.sidebar.slider(
    "⭐ Average rating",
    float(df["avg_rating"].min()),
    float(df["avg_rating"].max()),
    (3.0, 5.0),
    step=0.1
)

# Minimum ratings filter
min_ratings = st.sidebar.number_input(
    "📊 Minimum number of ratings",
    min_value=0,
    max_value=int(df["num_ratings"].max()),
    value=0,
    step=1000
)

top_n = st.sidebar.slider("🏆 Top N books to show", 5, 50, 10)

st.sidebar.markdown("---")
st.sidebar.caption(f"📊 Total books in dataset: {len(df):,}")

# =========================
# APPLY FILTERS
# =========================
filtered_df = df.copy()

if st.session_state.reset_trigger:
    st.session_state.reset_trigger = False
else:
    # Filter by rating
    filtered_df = filtered_df[
        filtered_df["avg_rating"].between(rating_min, rating_max)
    ]
    
    # Filter by number of ratings
    filtered_df = filtered_df[filtered_df["num_ratings"] >= min_ratings]
    
    # Exact author filter
    if selected_author != "All authors":
        filtered_df = filtered_df[filtered_df["authors"] == selected_author]
    
    # ==========================================================
    # SEARCH
    # ==========================================================
    if search_query:
        search_lower = search_query.strip().lower()
        
        titles_lower = filtered_df["title"].fillna("").astype(str).str.lower()
        authors_lower = filtered_df["authors"].fillna("").astype(str).str.lower()
        
        if "Title only" in search_in:
            mask = titles_lower.str.contains(search_lower, na=False, regex=False)
        elif "Author only" in search_in:
            mask = authors_lower.str.contains(search_lower, na=False, regex=False)
        else:
            mask = titles_lower.str.contains(search_lower, na=False, regex=False) | \
                   authors_lower.str.contains(search_lower, na=False, regex=False)
        
        # If no results are found, try searching individual words
        if not mask.any() and " " in search_lower:
            for word in search_lower.split():
                if len(word) > 2:
                    if "Title only" in search_in:
                        word_mask = titles_lower.str.contains(word, na=False, regex=False)
                    elif "Author only" in search_in:
                        word_mask = authors_lower.str.contains(word, na=False, regex=False)
                    else:
                        word_mask = titles_lower.str.contains(word, na=False, regex=False) | \
                                   authors_lower.str.contains(word, na=False, regex=False)
                    mask = mask | word_mask
        
        filtered_df = filtered_df[mask]

# =========================
# MAIN TITLE
# =========================
st.title("📚 Interactive Book Explorer")
st.markdown("*Explore books, ratings, and popularity from Goodreads data*")

# =========================
# METRICS ROW
# =========================
col1, col2, col3, col4 = st.columns(4)
col1.metric("📖 Filtered books", f"{len(filtered_df):,}")
col2.metric("⭐ Avg rating", f"{filtered_df['avg_rating'].mean():.2f}" if len(filtered_df) > 0 else "N/A")
col3.metric("📊 Total ratings", f"{int(filtered_df['num_ratings'].sum()):,}" if len(filtered_df) > 0 else "0")
col4.metric("✍️ Unique authors", f"{filtered_df['authors'].nunique():,}" if len(filtered_df) > 0 else "0")

# Search information
if search_query and len(filtered_df) > 0:
    st.success(f"✅ Found **{len(filtered_df)}** books matching '{search_query}'")
elif search_query and len(filtered_df) == 0:
    st.error(f"❌ No books found matching '{search_query}'. Try different keywords.")

# =========================
# TABS
# =========================
tab1, tab2, tab3 = st.tabs(["📊 Overview", "🏆 Authors", "📖 Book Explorer"])

# =========================
# TAB 1: OVERVIEW (legend in the bottom-right corner)
# =========================
with tab1:
    if len(filtered_df) == 0:
        st.warning("⚠️ No books match the selected filters.")
    else:
        st.subheader("📈 Ratings vs Popularity")
        
        show_trendline = st.checkbox("📈 Show trend line", value=True)
        
        if show_trendline:
            trend_type = st.radio(
                "Trend line type:",
                ["Linear", "Logarithmic", "Polynomial (2nd degree)"],
                horizontal=True
            )
        else:
            trend_type = None
        
        fig = go.Figure()
        
        # ==================================================
        # DATA POINTS (BOOKS)
        # ==================================================
        fig.add_trace(go.Scatter(
            x=filtered_df["avg_rating"],
            y=filtered_df["num_ratings"],
            mode='markers',
            name='📚 Books',
            marker=dict(
                size=6,
                opacity=0.5,
                color=filtered_df["avg_rating"],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(
                    title="⭐ Rating",
                    x=1.02,
                    len=0.5,
                    thickness=15
                )
            ),
            text=filtered_df["title"],
            hovertemplate="<b>%{text}</b><br>✍️ Author: %{customdata[0]}<br>⭐ Rating: %{x:.2f}<br>📊 Ratings: %{y:,.0f}<extra></extra>",
            customdata=filtered_df[["authors"]],
            showlegend=True
        ))
        
        # ==================================================
        # TREND LINE
        # ==================================================
        if show_trendline and len(filtered_df) > 2:
            
            y_log = np.log10(filtered_df["num_ratings"].values + 1)
            x_vals = filtered_df["avg_rating"].values
            
            if trend_type == "Linear":
                coeffs = np.polyfit(x_vals, y_log, 1)
                slope, intercept = coeffs[0], coeffs[1]
                x_smooth = np.linspace(x_vals.min(), x_vals.max(), 100)
                y_smooth = 10 ** (slope * x_smooth + intercept)
                
                fig.add_trace(go.Scatter(
                    x=x_smooth, 
                    y=y_smooth, 
                    mode='lines',
                    name='📈 Linear trend',
                    line=dict(color='red', width=2, dash='dash'),
                    showlegend=True
                ))
                
            elif trend_type == "Logarithmic":
                log_x = np.log(x_vals + 0.01)
                coeffs = np.polyfit(log_x, y_log, 1)
                b, a = coeffs[0], coeffs[1]
                x_smooth = np.linspace(x_vals.min(), x_vals.max(), 100)
                y_smooth = 10 ** (a + b * np.log(x_smooth + 0.01))
                
                fig.add_trace(go.Scatter(
                    x=x_smooth, 
                    y=y_smooth, 
                    mode='lines',
                    name='📈 Logarithmic trend',
                    line=dict(color='orange', width=2, dash='dash'),
                    showlegend=True
                ))
                
            elif trend_type == "Polynomial (2nd degree)":
                coeffs = np.polyfit(x_vals, y_log, 2)
                x_smooth = np.linspace(x_vals.min(), x_vals.max(), 100)
                y_smooth = 10 ** (coeffs[0] * x_smooth**2 + coeffs[1] * x_smooth + coeffs[2])
                
                fig.add_trace(go.Scatter(
                    x=x_smooth, 
                    y=y_smooth, 
                    mode='lines',
                    name='📈 Polynomial trend',
                    line=dict(color='purple', width=2),
                    showlegend=True
                ))
        
        # ==================================================
        # CHART SETTINGS (legend in the bottom-right corner)
        # ==================================================
        fig.update_layout(
            title="Book Ratings vs Popularity" + (" (with trend line)" if show_trendline else ""),
            xaxis_title="⭐ Average Rating",
            yaxis_title="📊 Number of Ratings (log scale)",
            font=dict(size=12),
            height=550,
            hoverlabel=dict(bgcolor="white", font_size=12),
            legend=dict(
                x=1.21,
                y=0.75,
                xanchor='right',
                yanchor='bottom',
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="gray",
                borderwidth=1,
                font=dict(size=11)
            )
        )
        
        fig.update_yaxes(type="log")
        
        st.plotly_chart(fig, use_container_width=True)
        
        # ==================================================
        # BOOK DETAILS
        # ==================================================
        st.markdown("---")
        st.subheader("📖 Book Details")
        
        if len(filtered_df) > 0:
            selected_title = st.selectbox(
                "Select a book to see details:",
                filtered_df["title"].unique(),
                key="detail_selector"
            )
            
            if selected_title:
                book = filtered_df[filtered_df["title"] == selected_title].iloc[0]
                col_a, col_b, col_c, col_d = st.columns(4)
                
                with col_a:
                    st.info(f"**📖 Title**\n\n{book['title']}")
                
                with col_b:
                    st.info(f"**✍️ Author**\n\n{book['authors']}")
                
                with col_c:
                    st.info(f"**⭐ Rating**\n\n{book['avg_rating']} / 5.0")
                
                with col_d:
                    st.info(f"**📊 Ratings**\n\n{int(book['num_ratings']):,}")
        
        # ==================================================
        # HISTOGRAM
        # ==================================================
        st.subheader("📊 Rating Distribution")
        
        fig2 = px.histogram(
            filtered_df,
            x="avg_rating",
            nbins=30,
            opacity=0.7
        )
        
        fig2.update_layout(
            xaxis_title="⭐ Average Rating",
            yaxis_title="📊 Number of Books",
            height=400
        )
        
        st.plotly_chart(fig2, use_container_width=True)

# =========================
# TAB 2: AUTHORS
# =========================
with tab2:
    if len(filtered_df) > 0:
        
        author_df = filtered_df.groupby("authors").agg(
            avg_rating=("avg_rating", "mean"),
            total_books=("title", "count"),
            total_ratings=("num_ratings", "sum")
        ).reset_index()
        
        author_df = author_df.sort_values(
            "total_ratings",
            ascending=False
        ).head(15)
        
        fig3 = px.bar(
            author_df,
            x="authors",
            y="total_ratings",
            color="avg_rating",
            color_continuous_scale="Viridis",
            title="Top 15 Authors by Total Ratings"
        )
        
        fig3.update_layout(
            xaxis_tickangle=-45,
            height=500
        )
        
        st.plotly_chart(fig3, use_container_width=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏅 Highest Rated Authors (min 5 books)")
            
            high_rated = author_df[
                author_df["total_books"] >= 5
            ].sort_values(
                "avg_rating",
                ascending=False
            ).head(10)
            
            st.dataframe(
                high_rated[["authors", "avg_rating", "total_books"]],
                hide_index=True
            )
        
        with col2:
            st.subheader("📚 Most Prolific Authors")
            
            most_books = author_df.sort_values(
                "total_books",
                ascending=False
            ).head(10)
            
            st.dataframe(
                most_books[["authors", "total_books", "avg_rating"]],
                hide_index=True
            )
    
    else:
        st.warning("⚠️ No books match the current filters.")

# =========================
# TAB 3: BOOK EXPLORER
# =========================
with tab3:
    if len(filtered_df) > 0:
        
        col_left, col_right = st.columns([1, 1])
        
        with col_left:
            st.subheader("📖 Select a Book")
            
            selected_book = st.selectbox(
                "Choose a book to explore:",
                filtered_df["title"].unique(),
                key="explorer_select"
            )
            
            if selected_book:
                book = filtered_df[
                    filtered_df["title"] == selected_book
                ].iloc[0]
                
                st.markdown(f"**📖 Title:** {book['title']}")
                st.markdown(f"**✍️ Author:** {book['authors']}")
                st.markdown(f"**⭐ Rating:** {book['avg_rating']} / 5.0")
                st.markdown(f"**📊 Ratings:** {int(book['num_ratings']):,}")
        
        with col_right:
            st.subheader("📚 Recommended Books")
            
            if selected_book:
                book = filtered_df[
                    filtered_df["title"] == selected_book
                ].iloc[0]
                
                similar = filtered_df.copy()
                
                if similar["avg_rating"].max() > similar["avg_rating"].min():
                    rating_norm = (
                        (similar["avg_rating"] - similar["avg_rating"].min()) /
                        (similar["avg_rating"].max() - similar["avg_rating"].min())
                    )
                    
                    target_rating_norm = (
                        (book["avg_rating"] - similar["avg_rating"].min()) /
                        (similar["avg_rating"].max() - similar["avg_rating"].min())
                    )
                else:
                    rating_norm = 0
                    target_rating_norm = 0
                
                if similar["num_ratings"].max() > similar["num_ratings"].min():
                    pop_norm = (
                        (similar["num_ratings"] - similar["num_ratings"].min()) /
                        (similar["num_ratings"].max() - similar["num_ratings"].min())
                    )
                    
                    target_pop_norm = (
                        (book["num_ratings"] - similar["num_ratings"].min()) /
                        (similar["num_ratings"].max() - similar["num_ratings"].min())
                    )
                else:
                    pop_norm = 0
                    target_pop_norm = 0
                
                similar["score"] = (
                    abs(rating_norm - target_rating_norm) +
                    abs(pop_norm - target_pop_norm)
                )
                
                similar = similar[similar["title"] != book["title"]]
                
                recommendations = similar.sort_values("score").head(5)
                
                st.dataframe(
                    recommendations[
                        ["title", "authors", "avg_rating", "num_ratings"]
                    ],
                    hide_index=True
                )
                
                st.caption(
                    "💡 *Recommendations based on similar ratings and popularity*"
                )
        
        st.markdown("---")
        
        st.subheader(f"🏆 Top {top_n} Most Popular Books")
        
        top_books = filtered_df.sort_values(
            "num_ratings",
            ascending=False
        ).head(top_n)
        
        st.dataframe(
            top_books[
                ["title", "authors", "avg_rating", "num_ratings"]
            ],
            hide_index=True
        )
    
    else:
        st.warning("⚠️ No books match the current filters.")

# =========================
# RAW DATA
# =========================
with st.expander("🔍 Show raw data"):
    st.dataframe(filtered_df, use_container_width=True)

# =========================
# FOOTER
# =========================
st.markdown("---")

st.caption(
    f"📊 Dataset: {len(df):,} total books | "
    f"Showing: {len(filtered_df):,} books | "
    f"Built with Streamlit & Plotly"
)

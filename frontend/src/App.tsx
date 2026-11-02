import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Footer } from './components/Footer'
import { Navbar } from './components/Navbar'
import { AboutPage } from './pages/AboutPage'
import { AnalyzerPage, StyleguidePage } from './pages/AnalyzerPage'
import { EthicsPage } from './pages/EthicsPage'
import { HistoryPage } from './pages/HistoryPage'

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Navbar />
        <Routes>
          <Route path="/" element={<AnalyzerPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/ethics" element={<EthicsPage />} />
          {import.meta.env.DEV && <Route path="/styleguide" element={<StyleguidePage />} />}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <Footer />
      </div>
    </BrowserRouter>
  )
}

export default App

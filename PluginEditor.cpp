#include "PluginEditor.h"
#include <BinaryData.h>
#include "WigaWindowSize.h"
#include "NineHandsMenu.h"
#include "NineHandsGlow.h"

using namespace juce;

namespace
{
    // Repère du dessin (v2.0.0) : 935 x 900 unités = image 1870 x 1800 / 2 (tools/layout_v2.json, tools/v2/make_art_v2.py).
    // Format double : mêmes hauteurs de fenêtre que Ring Think (495 / 557 / 743 px), largeur selon les proportions
    // de la pédale -> 514 x 495 par défaut et au minimum (« 60 % »).
    constexpr int kW = 935, kH = 900;
    constexpr float kAsset = 2.0f;                               // résolution des images / repère
    constexpr float kRefH = 743.0f;                              // hauteur « 100 % » (= Ring Think à 100 %)
    const float kScales[3] = { 495.0f / 743.0f, 0.75f, 1.0f };
    constexpr float kDefaultScale = 495.0f / 743.0f;             // fenêtre par défaut (= taille minimale)

    // ---- commandes ----
    const Point<float> kKnob (553.0f, 285.0f);  constexpr float kKnobR = 42.0f, kKnobImg = 98.42f;          // RANGE (6 crans)
    const Point<float> kSmall[3] = { { 552.0f, 480.0f }, { 677.0f, 480.0f }, { 802.0f, 480.0f } };          // Q, PURR, BOOST
    constexpr float kSmallR = 36.8f, kSmallImg = 86.23f;
    const char* const kSmallId[3] = { "q", "purr", "boost" };
    const char* const kSmallName[3] = { "Q", "PURR", "BOOST" };
    const Rectangle<float> kScreen = Rectangle<float>::leftTopRightBottom (641.0f, 183.0f, 845.0f, 387.0f);   // zone d'affichage de la vitre
    constexpr float kScreenRadius = 8.0f;
    const Rectangle<float> kPill = Rectangle<float>::leftTopRightBottom (515.2f, 586.0f, 838.8f, 624.0f);   // presets / ligne d'état
    const Point<float> kFsC (677.0f, 705.0f);
    const Rectangle<float> kFs (kFsC.x - 72.75f, kFsC.y - 72.75f, 145.5f, 145.5f);  // footswitch (dans le fond) + reflet ambre
    constexpr float kFsBtnR = 28.98f, kFsHitR = 46.0f;
    const Point<float> kLedC (762.0f, 705.0f);
    const Rectangle<float> kLed (kLedC.x - 10.5f, kLedC.y - 10.5f, 21.0f, 21.0f);
    const Rectangle<float> kLedGlow (687.0f, 630.0f, 150.0f, 150.0f);       // façade éclairée par la LED (dosée par Glow)
    const Point<float> kTogC (812.0f, 107.5f);
    const Rectangle<float> kToggle (kTogC.x - 39.5f, kTogC.y - 39.5f, 79.0f, 79.0f);   // inverseur photo (haut = MAN, bas = AUTO)
    const Rectangle<float> kToggleHit (kTogC.x - 34.0f, kTogC.y - 62.0f, 68.0f, 124.0f);
    constexpr float kJackY = 450.0f, kOutX = 32.0f, kInX = 900.0f;
    const Rectangle<float> kCryLogo (677.0f - 107.5f, 804.0f - 30.0f, 215.0f, 60.0f);
    const Colour kInk (0xffe2e0de), kAmber (0xffffb040), kAmberHi (0xffffd690);
    constexpr int kFrames = 33;                                             // positions précalculées du plateau

    // plateau à plat (orteil enfoncé, tel que dans le design) ; il pivote autour de la charnière, côté talon
    constexpr float kPlateL = 47.5f, kPlateR = 447.0f, kPlateTop = 15.5f, kHingeY = 881.0f;
    const Rectangle<float> kPlate (kPlateL, kPlateTop, kPlateR - kPlateL, kHingeY - kPlateTop);
    constexpr float kRise = 10.0f, kWiden = 1.02f;                          // orteil levé : pointe plus haute et plus large (perspective)
    constexpr float kThick = 5.0f;                                          // épaisseur visible du plateau (tranches)

    Image loadPng (const void* d, int n) { return ImageFileFormat::loadFrom (d, (size_t) n).convertedToFormat (Image::ARGB); }

    // redimensionne une fois (par le timer, jamais dans paint), puis garde en cache tant que la taille ne change pas
    struct ScaledCache
    {
        Image src, img; float scale = -1.0f;
        void prepare (float s)           // s = pixels écran par unité du repère
        {
            if (std::abs (s - scale) <= 1.0e-4f && img.isValid()) return;
            scale = s;
            const float k = s / kAsset;
            const int w = jmax (1, roundToInt ((float) src.getWidth() * k)), h = jmax (1, roundToInt ((float) src.getHeight() * k));
            img = src.rescaled (w, h, Graphics::highResamplingQuality);
        }
        // anti-gel v2 : le cache s'il existe, sinon l'image d'origine en attendant le timer
        const Image& get() const { return img.isValid() ? img : src; }
    };

    //==========================================================================
    struct Homography
    {
        double h[9] {};
        // calcule H tel que H(dst[i]) = src[i] (4 couples de points)
        bool solve (const Point<double> dst[4], const Point<double> src[4])
        {
            double A[8][9] {};
            for (int i = 0; i < 4; ++i)
            {
                const double x = dst[i].x, y = dst[i].y, u = src[i].x, v = src[i].y;
                double r1[9] = { x, y, 1, 0, 0, 0, -u * x, -u * y, u };
                double r2[9] = { 0, 0, 0, x, y, 1, -v * x, -v * y, v };
                std::copy (r1, r1 + 9, A[2 * i]); std::copy (r2, r2 + 9, A[2 * i + 1]);
            }
            for (int c = 0; c < 8; ++c)
            {
                int piv = c;
                for (int r = c + 1; r < 8; ++r) if (std::abs (A[r][c]) > std::abs (A[piv][c])) piv = r;
                if (std::abs (A[piv][c]) < 1e-12) return false;
                for (int k = 0; k < 9; ++k) std::swap (A[c][k], A[piv][k]);
                for (int r = 0; r < 8; ++r)
                    if (r != c)
                    {
                        const double f = A[r][c] / A[c][c];
                        for (int k = c; k < 9; ++k) A[r][k] -= f * A[c][k];
                    }
            }
            for (int i = 0; i < 8; ++i) h[i] = A[i][8] / A[i][i];
            h[8] = 1.0;
            return true;
        }
        Point<double> map (double x, double y) const
        {
            const double w = h[6] * x + h[7] * y + h[8];
            return { (h[0] * x + h[1] * y + h[2]) / w, (h[3] * x + h[4] * y + h[5]) / w };
        }
    };

    //==========================================================================
    // Plateau en mouvement. Chaque position est une perspective exacte du calque « orteil enfoncé », avec :
    //   - la face du plateau qui s'assombrit en se relevant (elle s'écarte de la lumière, en haut à gauche) et un reflet
    //     qui glisse sur le chrome pendant la bascule,
    //   - les tranches visibles quand la pointe monte (tranche de pointe et tranche gauche éclairées, tranche droite dans l'ombre),
    //   - une ombre portée qui s'allonge et s'adoucit avec la hauteur (nulle à la charnière, maximale à la pointe),
    //   - la charnière : le talon s'enfonce dans son logement, une fente sombre s'ouvre et l'axe accroche la lumière.
    class TreadleWarp
    {
    public:
        void setSource (Image downImg)
        {
            down = std::move (downImg);
            const float cx = 0.5f * (kPlateL + kPlateR);
            box = Rectangle<float> (cx - (cx - kPlateL) * kWiden - kThick - 6.0f, jmax (0.0f, kPlateTop - kRise - kThick - 4.0f),
                                    (kPlateR - kPlateL) * kWiden + 2.0f * kThick + 34.0f, 0.0f);
            box = box.withBottom (kHingeY + 34.0f).getSmallestIntegerContainer().toFloat().getIntersection ({ 0.0f, 0.0f, (float) kW, (float) kH });
            scale = -1.0f;
        }
        Rectangle<float> designBounds() const { return box; }

        void prepare (float s)
        {
            if (std::abs (s - scale) < 1.0e-4f) return;
            scale = s;
            const int bw = jmax (1, roundToInt (box.getWidth() * s)), bh = jmax (1, roundToInt (box.getHeight() * s));
            src = down.getClippedImage ((box * kAsset).getSmallestIntegerContainer()).rescaled (bw, bh, Graphics::highResamplingQuality)
                      .convertedToFormat (Image::ARGB);
            // anti-gel v2 : les anciennes positions restent affichables en attendant les nouvelles (pas de saut visuel)
            for (size_t i = 0; i < frames.size(); ++i) { if (frames[i].isValid()) oldFrames[i] = frames[i]; frames[i] = {}; }
        }

        // t = 0 : orteil levé (talon enfoncé), t = 1 : orteil enfoncé
        // Anti-gel v2 : le dessin n'utilise que des positions déjà calculées (la plus proche, ou celle de l'ancienne
        // taille) ; aucune n'est calculée dans paint. Renvoie nullptr si rien n'est encore prêt.
        const Image* frame (int i) const
        {
            i = jlimit (0, kFrames - 1, i);
            for (auto* set : { &frames, &oldFrames })
                for (int d = 0; d < kFrames; ++d)
                {
                    if (i - d >= 0 && (*set)[(size_t) (i - d)].isValid()) return &(*set)[(size_t) (i - d)];
                    if (i + d < kFrames && (*set)[(size_t) (i + d)].isValid()) return &(*set)[(size_t) (i + d)];
                }
            return nullptr;
        }
        bool isReady (int i) const { return frames[(size_t) jlimit (0, kFrames - 1, i)].isValid(); }
        // en attendant la première position : le calque d'origine (orteil enfoncé), sans calcul
        void drawOriginal (Graphics& g, Rectangle<float> dest) const
        {
            const auto sr = (box * kAsset).getSmallestIntegerContainer();
            g.drawImage (down, roundToInt (dest.getX()), roundToInt (dest.getY()), roundToInt (dest.getWidth()), roundToInt (dest.getHeight()),
                         sr.getX(), sr.getY(), sr.getWidth(), sr.getHeight());
        }

        // calcule à l'avance une position manquante, en partant de la position actuelle (appelé par le timer)
        bool buildNextMissing (int around)
        {
            if (scale < 0.0f) return false;
            around = jlimit (0, kFrames - 1, around);
            for (int d = 0; d < kFrames; ++d)
                for (int i : { around - d, around + d })
                    if (i >= 0 && i < kFrames && ! frames[(size_t) i].isValid())
                    { frames[(size_t) i] = build ((float) i / (float) (kFrames - 1)); return true; }
            for (auto& f : oldFrames) f = {};      // toutes les positions sont prêtes : on libère les anciennes
            return false;
        }

    private:
        static uint8 u8 (float v) { return (uint8) jlimit (0, 255, roundToInt (v)); }

        Image build (float t) const
        {
            const int w = src.getWidth(), h = src.getHeight();
            const double sx = (double) w / box.getWidth(), sy = (double) h / box.getHeight();
            auto loc = [&] (double x, double y) { return Point<double> ((x - box.getX()) * sx, (y - box.getY()) * sy); };
            // inclinaison (comme Wharry) : 1 = pointe levée, 0 = plateau à plat (pédale à 80 %), < 0 = pointe enfoncée au-delà du plat
            const double sTilt = jlimit (-0.25, 1.0, (0.8 - (double) t) / 0.8);
            const double cx = 0.5 * (kPlateL + kPlateR), lift = jmax (0.0, sTilt);
            const double wid = 1.0 + (kWiden - 1.0) * lift, rise = kRise * lift;
            const Point<double> srcQ[4] = { loc (kPlateL, kPlateTop), loc (kPlateR, kPlateTop), loc (kPlateR, kHingeY), loc (kPlateL, kHingeY) };
            const Point<double> dstQ[4] = { loc (cx - (cx - kPlateL) * wid, kPlateTop - rise), loc (cx + (kPlateR - cx) * wid, kPlateTop - rise),
                                            loc (kPlateR, kHingeY), loc (kPlateL, kHingeY) };
            Homography H;
            const bool warp = lift > 1.0e-4 && H.solve (dstQ, srcQ);

            // ---------- 1) face du plateau en perspective ----------
            Image plate (Image::ARGB, w, h, true);
            {
                const Image::BitmapData bs (src, Image::BitmapData::readOnly);
                Image::BitmapData bo (plate, Image::BitmapData::writeOnly);
                const double topY = dstQ[0].y, botY = dstQ[3].y, span = jmax (1.0, botY - topY);
                // reflet : bande douce et légèrement oblique (lumière en haut à gauche) qui glisse le long du plateau
                const double bandC = 0.10 + 0.55 * (double) t;                 // 0 = pointe, 1 = charnière
                const double bandW = 0.16, bandK = 0.16 + 0.10 * lift;
                for (int y = 0; y < h; ++y)
                {
                    const double gy = jlimit (0.0, 1.0, (botY - (double) y) / span);   // 1 = pointe, 0 = charnière
                    // diffus : la pointe levée se tourne vers la lumière, enfoncée elle s'en détourne ; creux sombre près de la charnière
                    const float gain = (float) (1.0 + 0.13 * sTilt * std::pow (gy, 1.3) - 0.07 * lift * std::pow (1.0 - gy, 5.0));
                    for (int x = 0; x < w; ++x)
                    {
                        double u = x, v = y;
                        if (warp) { const auto q = H.map (x + 0.5, y + 0.5); u = q.x - 0.5; v = q.y - 0.5; }
                        if (u < -1.0 || v < -1.0 || u > w || v > h) continue;
                        const PixelARGB p = sample (bs, w, h, (float) u, (float) v);
                        if (p.getAlpha() == 0) continue;
                        const double xr = (double) x / (double) w;
                        const double bpos = (1.0 - gy) + 0.22 * (xr - 0.5);
                        const float a = (float) p.getAlpha();
                        // le chrome brille, le caoutchouc noir reste mat (reflet pondéré par la luminance du pixel)
                        const float lumK = jlimit (0.2f, 1.0f, ((float) p.getRed() + (float) p.getGreen() + (float) p.getBlue()) / 3.0f
                                                                * 255.0f / jmax (1.0f, a) / 160.0f);
                        const float bnd = lumK * (float) (bandK * std::exp (-0.5 * std::pow ((bpos - bandC) / bandW, 2.0)));
                        auto ch = [&] (uint8 c)
                        {
                            const float v1 = jmin (a, (float) c * gain);
                            return u8 (v1 + (a - v1) * bnd);                                    // le reflet éclaircit vers le blanc
                        };
                        PixelARGB o; o.setARGB (p.getAlpha(), ch (p.getRed()), ch (p.getGreen()), ch (p.getBlue()));
                        *(PixelARGB*) bo.getPixelPointer (x, y) = o;
                    }
                }
            }

            // ---------- 2) tranches, extrudées depuis la silhouette réelle du plateau (coins arrondis compris) ----------
            Image out (Image::ARGB, w, h, true);
            {
                const Image::BitmapData bp (plate, Image::BitmapData::readOnly);
                Image::BitmapData bo (out, Image::BitmapData::readWrite);
                auto alphaAt = [&] (int x, int y) { return ((const PixelARGB*) bp.getPixelPointer (x, y))->getAlpha(); };
                auto put = [&] (int x, int y, float a, int r, int g, int b)
                {
                    if (x < 0 || y < 0 || x >= w || y >= h || a <= 0.0f) return;
                    auto* px = (PixelARGB*) bo.getPixelPointer (x, y);
                    const float k = jmin (1.0f, a);
                    PixelARGB o;   // prémultiplié
                    o.setARGB (u8 (255.0f * k + px->getAlpha() * (1.0f - k)), u8 (r * k + px->getRed() * (1.0f - k)),
                               u8 (g * k + px->getGreen() * (1.0f - k)), u8 (b * k + px->getBlue() * (1.0f - k)));
                    *px = o;
                };
                const double th = kThick * sy * lift;                        // épaisseur apparente à la pointe
                const double topY = dstQ[0].y, botY = dstQ[3].y;
                // tranche de pointe : tournée vers le haut, elle accroche la lumière
                for (int x = 0; x < w; ++x)
                {
                    int yt = -1;
                    for (int y = 0; y < h; ++y) if (alphaAt (x, y) >= 128) { yt = y; break; }
                    if (yt < 0 || yt > topY + 40.0 * sy) continue;
                    const double ux = (double) x / (double) w;
                    const double fh = th * jlimit (0.0, 1.0, 1.0 - ((double) yt - topY) / (34.0 * sy));
                    for (int k = 1; k <= (int) std::ceil (fh) + 1; ++k)
                    {
                        const float cov = (float) jlimit (0.0, 1.0, fh - (k - 1) + 0.3);
                        const double u = (double) k / jmax (0.5, fh);
                        const int base = (int) (208 - 100 * u - 28 * ux);
                        put (x, yt - k, cov, base + 3, base + 2, base + 5);
                    }
                }
                // tranches latérales : épaisses à la pointe, nulles à la charnière ; gauche éclairée, droite dans l'ombre
                for (int y = 0; y < h; ++y)
                {
                    const double v = jlimit (0.0, 1.0, ((double) y - topY) / jmax (1.0, botY - topY));
                    const double fw = 0.55 * th * (1.0 - v);
                    if (fw < 0.25) continue;
                    int xl = -1, xr = -1;
                    for (int x = 0; x < w; ++x) if (alphaAt (x, y) >= 128) { xl = x; break; }
                    for (int x = w - 1; x >= 0; --x) if (alphaAt (x, y) >= 128) { xr = x; break; }
                    if (xl < 0) continue;
                    for (int k = 1; k <= (int) std::ceil (fw) + 1; ++k)
                    {
                        const float cov = (float) jlimit (0.0, 1.0, fw - (k - 1) + 0.3);
                        const double u = (double) k / jmax (0.5, fw);
                        const int bl = (int) (178 - 72 * u - 25 * v), br = (int) (64 - 24 * u + 10 * v);
                        put (xl - k, y, cov, bl + 4, bl + 3, bl + 6);
                        put (xr + k, y, cov, br + 4, br + 3, br + 6);
                    }
                }
                // face du plateau posée sur les tranches
                for (int y = 0; y < h; ++y)
                    for (int x = 0; x < w; ++x)
                    {
                        const PixelARGB o = *(const PixelARGB*) bp.getPixelPointer (x, y);
                        if (o.getAlpha() == 0) continue;
                        auto* px = (PixelARGB*) bo.getPixelPointer (x, y);
                        const float ka = (float) o.getAlpha() / 255.0f;
                        PixelARGB m;
                        m.setARGB (u8 (o.getAlpha() + px->getAlpha() * (1.0f - ka)), u8 (o.getRed() + px->getRed() * (1.0f - ka)),
                                   u8 (o.getGreen() + px->getGreen() * (1.0f - ka)), u8 (o.getBlue() + px->getBlue() * (1.0f - ka)));
                        *px = m;
                    }
            }

            // ---------- 3) charnière : le talon plonge, une fente sombre s'ouvre, l'axe accroche la lumière ----------
            {
                Image::BitmapData bo (out, Image::BitmapData::readWrite);
                const int yh = (int) std::round (dstQ[3].y);
                const int x0 = (int) std::ceil (dstQ[3].x + 18 * sx), x1 = (int) std::floor (dstQ[2].x - 18 * sx);
                const int gap = jmax (1, (int) std::round (3.5 * sy * lift));
                for (int x = jmax (0, x0); x <= jmin (w - 1, x1); ++x)
                {
                    const float fx = (float) jmin (x - x0, x1 - x) / (float) (12 * sx);
                    const float edgeK = jlimit (0.0f, 1.0f, fx);
                    for (int k = -gap; k <= gap; ++k)                      // fente sombre à cheval sur l'arête du talon
                    {
                        const int y = yh + k;
                        if (y < 0 || y >= h) continue;
                        auto* px = (PixelARGB*) bo.getPixelPointer (x, y);
                        const float a = (float) (0.75 * lift) * edgeK * (1.0f - std::abs ((float) k) / (float) (gap + 1));
                        PixelARGB o;
                        o.setARGB (u8 (px->getAlpha() + (255 - px->getAlpha()) * a), u8 (px->getRed() * (1 - a)), u8 (px->getGreen() * (1 - a)), u8 (px->getBlue() * (1 - a)));
                        *px = o;
                    }
                    // fin liseré clair : l'axe de la charnière éclairé juste sous la fente
                    const int yl = yh + gap + 1;
                    if (yl >= 0 && yl < h)
                    {
                        auto* px = (PixelARGB*) bo.getPixelPointer (x, yl);
                        const float a = (float) (0.35 * lift) * edgeK;
                        PixelARGB o;
                        o.setARGB (u8 (px->getAlpha() + (255 - px->getAlpha()) * a), u8 (px->getRed() + (210 - px->getRed()) * a),
                                   u8 (px->getGreen() + (208 - px->getGreen()) * a), u8 (px->getBlue() + (205 - px->getBlue()) * a));
                        *px = o;
                    }
                }
            }

            // ---------- 4) ombre portée : celle de Wharry, agrandie x2 (v2.0.0, validée en GIF) ----------
            // Wharry (repère 1020 x 928) : décalage (2 + 8 lift, 3 + 11 lift), flou boîte 3 + 5 lift (2 passes),
            // force 0,32 + 0,30 lift ; ici x2 en distance, x1,4 en flou, ramené au repère 935 x 900 (x 0,97)
            std::vector<float> sh ((size_t) (w * h), 0.0f), tmp ((size_t) (w * h), 0.0f);
            {
                const Image::BitmapData bp (out, Image::BitmapData::readOnly);
                const int ox = roundToInt (2.0 * 0.97 * (2.0 + 8.0 * lift) * sx), oy = roundToInt (2.0 * 0.97 * (3.0 + 11.0 * lift) * sy);
                for (int y = 0; y < h; ++y)
                    for (int x = 0; x < w; ++x)
                    {
                        const int xs = x - ox, ys = y - oy;
                        if (xs >= 0 && ys >= 0 && xs < w && ys < h)
                            sh[(size_t) (y * w + x)] = (float) ((const PixelARGB*) bp.getPixelPointer (xs, ys))->getAlpha() / 255.0f;
                    }
            }
            const int rad = jmax (1, roundToInt (1.4 * 0.97 * (3.0 + 5.0 * lift) * sx));
            const float norm = 1.0f / (float) (2 * rad + 1);
            for (int pass = 0; pass < 2; ++pass)      // flou boîte séparable, 2 passes (~ gaussien)
            {
                for (int y = 0; y < h; ++y)
                {
                    float acc = 0.0f;
                    for (int x = -rad; x < w + rad; ++x)
                    {
                        if (x + rad < w) acc += sh[(size_t) (y * w + x + rad)];
                        if (x - rad - 1 >= 0) acc -= sh[(size_t) (y * w + x - rad - 1)];
                        if (x >= 0 && x < w) tmp[(size_t) (y * w + x)] = acc * norm;
                    }
                }
                for (int x = 0; x < w; ++x)
                {
                    float acc = 0.0f;
                    for (int y = -rad; y < h + rad; ++y)
                    {
                        if (y + rad < h) acc += tmp[(size_t) ((y + rad) * w + x)];
                        if (y - rad - 1 >= 0) acc -= tmp[(size_t) ((y - rad - 1) * w + x)];
                        if (y >= 0 && y < h) sh[(size_t) (y * w + x)] = acc * norm;
                    }
                }
            }
            Image res (Image::ARGB, w, h, true);
            {
                const Image::BitmapData bp (out, Image::BitmapData::readOnly);
                Image::BitmapData bo (res, Image::BitmapData::writeOnly);
                const float strength = (float) (0.32 + 0.30 * lift - 0.10 * jmin (0.0, sTilt));
                for (int y = 0; y < h; ++y)
                    for (int x = 0; x < w; ++x)
                    {
                        const PixelARGB pp = *(const PixelARGB*) bp.getPixelPointer (x, y);
                        const float pa = (float) pp.getAlpha() / 255.0f;
                        const float sa = sh[(size_t) (y * w + x)] * strength * (1.0f - pa);
                        PixelARGB o;   // prémultiplié : l'ombre noire n'ajoute que de l'alpha
                        o.setARGB (u8 ((pa + sa) * 255.0f), pp.getRed(), pp.getGreen(), pp.getBlue());
                        *(PixelARGB*) bo.getPixelPointer (x, y) = o;
                    }
            }
            return res;
        }

        static PixelARGB sample (const Image::BitmapData& bd, int w, int h, float x, float y)
        {
            const int x0 = (int) std::floor (x), y0 = (int) std::floor (y);
            const float fx = x - (float) x0, fy = y - (float) y0;
            auto px = [&] (int xx, int yy) -> PixelARGB
            {
                if (xx < 0 || yy < 0 || xx >= w || yy >= h) { PixelARGB z; z.setARGB (0, 0, 0, 0); return z; }
                return *(const PixelARGB*) bd.getPixelPointer (xx, yy);
            };
            const PixelARGB a = px (x0, y0), b = px (x0 + 1, y0), c = px (x0, y0 + 1), d = px (x0 + 1, y0 + 1);
            auto mix = [&] (int ca, int cb, int cc, int cd)
            {
                const float t = (float) ca + ((float) cb - (float) ca) * fx, u = (float) cc + ((float) cd - (float) cc) * fx;
                return u8 (t + (u - t) * fy);
            };
            PixelARGB o;
            o.setARGB (mix (a.getAlpha(), b.getAlpha(), c.getAlpha(), d.getAlpha()), mix (a.getRed(), b.getRed(), c.getRed(), d.getRed()),
                       mix (a.getGreen(), b.getGreen(), c.getGreen(), d.getGreen()), mix (a.getBlue(), b.getBlue(), c.getBlue(), d.getBlue()));
            return o;
        }

        Image down, src;
        Rectangle<float> box { 0, 0, (float) kW, (float) kH };
        float scale = -1.0f;
        std::array<Image, kFrames> frames, oldFrames;
    };

    //==========================================================================
    // menu de taille de fenêtre (identique à Ring Think / Wharry) + taille par défaut des nouvelles fenêtres (comme Octopus)
    constexpr int kNumSizes = 3;           // 60 % (défaut d'origine) / 75 % / 100 %

    void addSizeItems (PopupMenu& m, const CrycatEditor* ed)
    {
        const int cur = ed != nullptr ? ed->getScaleIndex() : -1;
        const int def = WigaWindowSize::defaultIndex (JucePlugin_Name, kNumSizes);
        const char* names[kNumSizes] = { "60 %", "75 %", "100 %" };
        PopupMenu defSizes;
        for (int i = 0; i < kNumSizes; ++i)
        {
            m.addItem (901 + i, String (names[i]) + (i == def ? "  (default)" : ""), true, cur == i);
            defSizes.addItem (911 + i, names[i], true, i == def);
        }
        m.addSeparator();
        m.addSubMenu ("Default size (new windows)", defSizes);
    }

    void handleSizeChoice (int r, CrycatEditor* ed)
    {
        if (ed == nullptr) return;
        if (r >= 901 && r < 901 + kNumSizes) ed->setScaleIndex (r - 901);
        else if (r >= 911 && r < 911 + kNumSizes)
        {
            WigaWindowSize::setDefaultIndex (JucePlugin_Name, r - 911);   // toutes les nouvelles fenêtres de ce plugin
            ed->setScaleIndex (r - 911);                                  // et cette fenêtre tout de suite
        }
    }

    float rangeAngleDeg (int i) { return -125.0f + 50.0f * (float) jlimit (0, crycat::kNumRanges - 1, i); }
    Point<float> rangeNumberPos (int i)
    {
        const float a = degreesToRadians (rangeAngleDeg (i)), r = kKnobR + 21.0f;
        return { kKnob.x + std::sin (a) * r, kKnob.y - std::cos (a) * r };
    }

    // index d'un potard : seul calque qui tourne (ombre, chapeau « spun » et bague sont fixes et dans le fond) ;
    // flou de mouvement selon l'angle parcouru (montée immédiate, retombée x0,6 par image, pas de 3° au plus)
    struct MarkerAnim
    {
        float shown = -1000.0f, last = -1000.0f, span = 0.0f, dir = 1.0f, drawnSpan = -1.0f;
        bool step (float a)                         // a en degrés ; renvoie true si l'image change
        {
            if (shown < -999.0f) { shown = last = a; return true; }
            const float v = a - last; last = a;
            if (std::abs (v) > 1.0e-3f) dir = v > 0.0f ? 1.0f : -1.0f;
            span = jmax (jmin (std::abs (v), 40.0f), span * 0.6f);
            if (span < 0.15f) span = 0.0f;
            const bool ch = std::abs (a - shown) > 1.0e-3f || std::abs (span - drawnSpan) > 1.0e-3f;
            shown = a; drawnSpan = span;
            return ch;
        }
    };
}

//==============================================================================
class PedalView : public Component, private Timer
{
public:
    explicit PedalView (CrycatProcessor& p) : proc (p)
    {
        bg.src      = loadPng (BinaryData::background_png, BinaryData::background_pngSize);
        fsRefl.src  = loadPng (BinaryData::fs_refl_png, BinaryData::fs_refl_pngSize);
        ledOn.src   = loadPng (BinaryData::led_on_png, BinaryData::led_on_pngSize);
        ledGlow.src = loadPng (BinaryData::led_glow_png, BinaryData::led_glow_pngSize);
        {
            const auto strip = loadPng (BinaryData::toggle_strip_png, BinaryData::toggle_strip_pngSize);
            const int fw = strip.getWidth();
            for (int i = 0; i < 3; ++i) tg[i].src = strip.getClippedImage ({ 0, i * fw, fw, fw }).createCopy();
        }
        markerSrc = loadPng (BinaryData::knob_marker_png, BinaryData::knob_marker_pngSize);
        treadle.setSource (loadPng (BinaryData::treadle_down_png, BinaryData::treadle_down_pngSize));
        tfReg  = Typeface::createSystemTypefaceFor (BinaryData::PoppinsRegular_ttf, BinaryData::PoppinsRegular_ttfSize);
        tfMed  = Typeface::createSystemTypefaceFor (BinaryData::PoppinsMedium_ttf, BinaryData::PoppinsMedium_ttfSize);
        tfBold = Typeface::createSystemTypefaceFor (BinaryData::PoppinsBold_ttf, BinaryData::PoppinsBold_ttfSize);
        cryLogo = Drawable::createFromImageData (BinaryData::Crycat_Logo_White_svg, BinaryData::Crycat_Logo_White_svgSize);
        if (cryLogo != nullptr) cryLogo->replaceColour (Colours::white, kInk);
        menuLnf.f = { tfReg, tfMed, tfBold };
        glow = (float) NineHandsGlow::percent (JucePlugin_Name) / 100.0f;
        setOpaque (true);
        setMouseCursor (MouseCursor::NormalCursor);
        startTimerHz (30);
    }
    ~PedalView() override { stopTimer(); }

    // anti-gel v2 : jamais de calcul lourd ici, les caches seront refaits par le timer quand la taille sera stable
    void resized() override { s = (float) getWidth() / (float) kW; resizeSettle = 4; repaint(); }

    // caches d'images à la taille réelle en pixels (fenêtre x échelle Windows / Retina) : appelé par le timer
    // (et une fois à l'ouverture de la fenêtre), jamais par paint
    void rebuildCaches()
    {
        if (getWidth() <= 0) return;
        const float ps = s * dispScale;
        for (auto* c : { &bg, &fsRefl, &ledOn, &ledGlow, &tg[0], &tg[1], &tg[2] }) c->prepare (ps);
        auto fitMarker = [&] (float units) { const int px = jmax (4, roundToInt (units * ps)); return markerSrc.rescaled (px, px, Graphics::highResamplingQuality); };
        markerBig = fitMarker (kKnobImg); markerSmall = fitMarker (kSmallImg);
        buildPrint (ps);
        treadle.prepare (ps);
        askRepaint (getLocalBounds());
    }

    void paint (Graphics& g) override
    {
        // anti-gel v2 : aucun rescale ni calcul de cache ici, on dessine les caches existants (ou les originaux)
        lastPaintMs = Time::getMillisecondCounterHiRes();
        repaintAskedMs = 0.0;
        g.fillAll (Colour (0xff111113));                      // derrière les jacks et les coins arrondis
        g.drawImage (bg.get(), getLocalBounds().toFloat());

        // ---- halo de la LED sur la façade (sous la sérigraphie), dosé par Glow ----
        if (ledLevel > 0.003f)
        {
            g.setOpacity (jmin (1.0f, ledLevel * glow));
            g.drawImage (ledGlow.get(), r (kLedGlow));
            g.setOpacity (1.0f);
        }
        // ---- sérigraphie vectorielle (cache à la résolution de l'écran) ----
        if (print.isValid()) g.drawImage (print, getLocalBounds().toFloat());
        else drawPrint (g, s);

        // ---- plateau (deux positions voisines fondues -> mouvement continu) : talon = pointe levée ----
        const float fpos = jlimit (0.0f, 1.0f, drawnPedal) * (float) (kFrames - 1);
        const int f0 = jlimit (0, kFrames - 1, (int) std::floor (fpos)), f1 = jmin (kFrames - 1, f0 + 1);
        const float fr = fpos - (float) f0;
        const auto tb = r (treadle.designBounds());
        if (auto* im0 = treadle.frame (f0))
        {
            g.drawImage (*im0, tb);
            if (fr > 0.02f && f1 != f0) if (auto* im1 = treadle.frame (f1)) { g.setOpacity (fr); g.drawImage (*im1, tb); g.setOpacity (1.0f); }
        }
        else treadle.drawOriginal (g, tb);

        // ---- RANGE : chiffres (celui choisi en ambre) + index ----
        for (int i = 0; i < crycat::kNumRanges; ++i)
        {
            const auto np = r (rangeNumberPos (i));
            g.setColour (i == drawnRange ? kAmber : kInk.withAlpha (0.92f));
            g.setFont (font (tfMed, 14.0f * s));
            g.drawText (String (i + 1), Rectangle<float> (np.x - 14.0f * s, np.y - 12.0f * s, 28.0f * s, 24.0f * s), Justification::centred);
        }
        drawMarker (g, markerBig, kKnob, kKnobImg, rangeAnim);
        for (int i = 0; i < 3; ++i) drawMarker (g, markerSmall, kSmall[i], kSmallImg, smallAnim[i]);

        // ---- inverseur MAN / AUTO : position intermédiaire affichée brièvement pendant la bascule ----
        {
            const bool moving = Time::getMillisecondCounterHiRes() < toggleMidUntil;
            g.drawImage ((moving ? tg[1] : (drawnAuto ? tg[2] : tg[0])).get(), r (kToggle));
        }

        // ---- footswitch (dans le fond) : reflet ambre de la LED sur l'écrou, assombri pendant l'appui (Echoflex) ----
        if (ledLevel > 0.003f) { g.setOpacity (jmin (1.0f, ledLevel)); g.drawImage (fsRefl.get(), r (kFs)); g.setOpacity (1.0f); }
        if (pressed)
        {
            const auto c = r (kFsC); const float pr = kFsBtnR * 0.92f * s;
            g.setColour (Colours::black.withAlpha (0.25f));
            g.fillEllipse (c.x - pr, c.y - pr, pr * 2.0f, pr * 2.0f);
        }
        if (ledLevel > 0.003f) { g.setOpacity (jmin (1.0f, ledLevel)); g.drawImage (ledOn.get(), r (kLed)); g.setOpacity (1.0f); }

        drawScreen (g);
        drawPill (g);
    }

    // ------------------------------------------------------------ souris
    void mouseMove (const MouseEvent& e) override
    {
        const auto p = e.position / s;
        int h = 0;
        if (kPill.contains (p)) h = p.x < kPill.getX() + 34.0f ? 1 : (p.x > kPill.getRight() - 34.0f ? 2 : 3);
        if (h != pillHover) { pillHover = h; repaint (r (kPill).toNearestInt().expanded (2)); }
    }
    void mouseExit (const MouseEvent&) override { if (pillHover != 0) { pillHover = 0; repaint (r (kPill).toNearestInt().expanded (2)); } }

    void mouseDown (const MouseEvent& e) override
    {
        const auto p = e.position / s;
        if (e.mods.isPopupMenu()) { showMenu (p); return; }
        drag = Drag::None;
        if (kPill.contains (p))
        {
            statusUntil = 0.0;                       // un clic fait revenir la barre de presets
            if (p.x < kPill.getX() + 34.0f) stepPreset (-1);
            else if (p.x > kPill.getRight() - 34.0f) stepPreset (1);
            else showPresetMenu();
            return;
        }
        if (kScreen.contains (p)) { showPresetMenu(); return; }
        for (int i = 0; i < crycat::kNumRanges; ++i)          // clic sur un numéro : plage directe
            if (p.getDistanceFrom (rangeNumberPos (i)) < 11.0f) { proc.setParamValue ("range", (float) i); return; }
        if (p.getDistanceFrom (kKnob) < kKnobR * 1.1f) { drag = Drag::Knob; dragStartY = p.y; dragStartRange = currentRange(); return; }
        for (int i = 0; i < 3; ++i)
            if (p.getDistanceFrom (kSmall[i]) < kSmallR * 1.15f)
            {
                drag = (Drag) ((int) Drag::Small0 + i); dragStartY = p.y;
                if (auto* par = proc.apvts.getParameter (kSmallId[i])) { dragStartVal = par->getValue(); par->beginChangeGesture(); }
                return;
            }
        if (kToggleHit.contains (p)) { proc.togglePedalSwitch ("auto"); return; }   // l'animation suit le paramètre (timer)
        if (kFsC.getDistanceFrom (p) < kFsHitR) { pressed = true; proc.togglePedalSwitch ("active"); repaint (r (kFs).toNearestInt().expanded (4)); return; }   // Echoflex : bascule à l'appui
        if (kPlate.contains (p))
        {
            drag = Drag::Pedal; dragStartY = p.y;
            dragStartVal = proc.apvts.getRawParameterValue ("pedal")->load();
            if (auto* par = proc.apvts.getParameter ("pedal")) par->beginChangeGesture();
        }
    }

    void mouseDrag (const MouseEvent& e) override
    {
        const auto p = e.position / s;
        const float fine = e.mods.isShiftDown() ? 5.0f : 1.0f;
        if (drag == Drag::Knob)
        {
            const int nr = jlimit (0, crycat::kNumRanges - 1, dragStartRange + (int) std::lround ((dragStartY - p.y) / 22.0f));
            if (nr != currentRange()) proc.setParamValue ("range", (float) nr);
        }
        else if (drag == Drag::Pedal)
        {
            // tirer vers le bas = appuyer sur la pointe (son aigu)
            const float v = jlimit (0.0f, 1.0f, dragStartVal + (p.y - dragStartY) / (kPlate.getHeight() * 0.7f * fine));
            if (auto* par = proc.apvts.getParameter ("pedal")) par->setValueNotifyingHost (v);
        }
        else if (drag >= Drag::Small0)
        {
            const float v = jlimit (0.0f, 1.0f, dragStartVal + (dragStartY - p.y) / (220.0f * fine));
            if (auto* par = proc.apvts.getParameter (kSmallId[(int) drag - (int) Drag::Small0])) par->setValueNotifyingHost (v);
        }
    }

    void mouseUp (const MouseEvent&) override
    {
        if (drag == Drag::Pedal) if (auto* par = proc.apvts.getParameter ("pedal")) par->endChangeGesture();
        if (drag >= Drag::Small0) if (auto* par = proc.apvts.getParameter (kSmallId[(int) drag - (int) Drag::Small0])) par->endChangeGesture();
        drag = Drag::None;
        if (pressed) { pressed = false; repaint (r (kFs).toNearestInt().expanded (4)); }
    }

    void mouseDoubleClick (const MouseEvent& e) override
    {
        const auto p = e.position / s;
        if (kPlate.contains (p))              // double-clic sur le plateau : talon / pointe
            proc.setParamValue ("pedal", proc.apvts.getRawParameterValue ("pedal")->load() > 0.5f ? 0.0f : 1.0f);
        for (int i = 0; i < 3; ++i)           // double-clic sur un bouton : valeur par défaut
            if (p.getDistanceFrom (kSmall[i]) < kSmallR * 1.15f)
                if (auto* par = proc.apvts.getParameter (kSmallId[i])) { par->beginChangeGesture(); par->setValueNotifyingHost (par->getDefaultValue()); par->endChangeGesture(); }
    }

    void mouseWheelMove (const MouseEvent& e, const MouseWheelDetails& w) override
    {
        const auto p = e.position / s;
        if (p.getDistanceFrom (kKnob) < kKnobR * 1.1f)
            proc.setParamValue ("range", (float) jlimit (0, crycat::kNumRanges - 1, currentRange() + (w.deltaY > 0 ? 1 : -1)));
        else if (kPlate.contains (p))
            proc.setParamValue ("pedal", jlimit (0.0f, 1.0f, proc.apvts.getRawParameterValue ("pedal")->load() - w.deltaY * 0.25f));
        else if (kPill.contains (p))
            stepPreset (w.deltaY > 0 ? -1 : 1);
        else
            for (int i = 0; i < 3; ++i)
                if (p.getDistanceFrom (kSmall[i]) < kSmallR * 1.15f)
                    if (auto* par = proc.apvts.getParameter (kSmallId[i]))
                    { par->beginChangeGesture(); par->setValueNotifyingHost (jlimit (0.0f, 1.0f, par->getValue() + w.deltaY * 0.1f)); par->endChangeGesture(); }
    }

private:
    enum class Drag { None, Knob, Pedal, Small0, Small1, Small2 };

    Rectangle<float> r (Rectangle<float> d) const { return d * s; }
    Point<float> r (Point<float> d) const { return d * s; }
    static Font font (const Typeface::Ptr& tf, float pointHeight) { return Font (FontOptions (tf).withPointHeight (pointHeight)); }
    float physScale() const
    {
        if (auto* d = Desktop::getInstance().getDisplays().getDisplayForRect (getScreenBounds())) return jmax (1.0f, (float) d->scale);
        return 1.0f;
    }

    // anti-gel v2 : chaque redessin demandé par le timer est noté pour le chien de garde
    void askRepaint (Rectangle<int> area)
    {
        if (repaintAskedMs <= 0.0) repaintAskedMs = Time::getMillisecondCounterHiRes();
        repaint (area);
    }
    int currentRange() const { return jlimit (0, crycat::kNumRanges - 1, (int) std::lround (proc.apvts.getRawParameterValue ("range")->load())); }
    bool param (const char* id) const { return proc.apvts.getRawParameterValue (id)->load() > 0.5f; }

    // ------------------------------------------------------------ sérigraphie (Poppins + logo SVG), en unités x k
    void spaced (Graphics& g, const String& t, Point<float> c, const Typeface::Ptr& tf, float size, float spacing, float k)
    {
        auto f = font (tf, size * k);
        f = f.withExtraKerningFactor (spacing * k / jmax (1.0f, f.getHeight()));
        g.setFont (f);
        const float w = GlyphArrangement::getStringWidth (f, t) - spacing * k;      // pas d'espace après la dernière lettre
        g.drawText (t, Rectangle<float> (c.x * k - w * 0.5f, c.y * k - size * k, w + spacing * k + 2.0f, size * 2.0f * k), Justification::centredLeft, false);
    }
    void drawPrint (Graphics& g, float k)
    {
        const auto ink = kInk.withAlpha (0.92f);
        g.setColour (ink);
        auto tick = [&] (Point<float> c, float a, float r0, float r1, float w)
        {
            const Point<float> d (std::sin (a), -std::cos (a));
            g.drawLine ({ (c + d * r0) * k, (c + d * r1) * k }, w * k);
        };
        for (int i = 0; i < crycat::kNumRanges; ++i) tick (kKnob, degreesToRadians (rangeAngleDeg (i)), kKnobR + 5.0f, kKnobR + 11.0f, 1.75f);
        g.setFont (font (tfReg, 10.5f * k));
        g.drawText ("LOW",  Rectangle<float> ((kKnob.x - kKnobR - 15.0f - 20.0f) * k, (kKnob.y + kKnobR + 19.0f - 8.0f) * k, 40.0f * k, 16.0f * k), Justification::centred);
        g.drawText ("HIGH", Rectangle<float> ((kKnob.x + kKnobR + 15.0f - 20.0f) * k, (kKnob.y + kKnobR + 19.0f - 8.0f) * k, 40.0f * k, 16.0f * k), Justification::centred);
        spaced (g, "RANGE", { kKnob.x, kKnob.y + kKnobR + 36.0f }, tfMed, 13.0f, 2.5f, k);
        for (int i = 0; i < 3; ++i)
        {
            for (int t = 0; t <= 10; ++t)
                tick (kSmall[i], degreesToRadians (-135.0f + 27.0f * (float) t), kSmallR + 4.5f, kSmallR + ((t % 5) == 0 ? 11.5f : 8.5f), 1.3f);
            spaced (g, kSmallName[i], { kSmall[i].x, kSmall[i].y + kSmallR + 26.0f }, tfMed, 13.0f, 1.75f, k);
        }
        spaced (g, "MAN",  { kTogC.x, kTogC.y - 49.0f }, tfMed, 14.0f, 1.5f, k);
        spaced (g, "AUTO", { kTogC.x, kTogC.y + 49.0f }, tfMed, 14.0f, 1.5f, k);
        g.setColour (kInk.withAlpha (0.30f));
        g.fillRect (497.0f * k, (410.0f - 0.5f) * k, 360.0f * k, jmax (1.0f, 1.0f * k));
        g.setColour (ink);
        for (int side = 0; side < 2; ++side)          // OUT à gauche (se lit de bas en haut), IN à droite (de haut en bas)
        {
            Graphics::ScopedSaveState ss (g);
            const Point<float> c (side == 0 ? kOutX : kInX, kJackY);
            g.addTransform (AffineTransform::rotation (side == 0 ? -MathConstants<float>::halfPi : MathConstants<float>::halfPi, c.x * k, c.y * k));
            g.setFont (font (tfMed, 16.5f * k));
            g.drawText (side == 0 ? "OUT" : "IN", Rectangle<float> ((c.x - 30.0f) * k, (c.y - 12.0f) * k, 60.0f * k, 24.0f * k), Justification::centred);
        }
        if (cryLogo != nullptr) cryLogo->drawWithin (g, kCryLogo * k, RectanglePlacement::centred, 0.92f);
    }
    void buildPrint (float ps)
    {
        const int w = jmax (1, roundToInt ((float) kW * ps)), h = jmax (1, roundToInt ((float) kH * ps));
        Image im (Image::ARGB, w, h, true);
        { Graphics g (im); drawPrint (g, ps); }
        print = im;
    }

    // index d'un potard, flou de mouvement par moyenne progressive (comme nh::Knob)
    void drawMarker (Graphics& g, const Image& img, Point<float> c0, float sizeUnits, const MarkerAnim& an)
    {
        const Image& im = img.isValid() ? img : markerSrc;
        const auto c = r (c0);
        const float sc = sizeUnits * s / (float) im.getWidth();
        auto place = [&] (float deg)
        {
            return AffineTransform::translation (-im.getWidth() * 0.5f, -im.getHeight() * 0.5f).scaled (sc)
                       .rotated (degreesToRadians (deg)).translated (c.x, c.y);
        };
        Graphics::ScopedSaveState ss (g);
        g.setImageResamplingQuality (Graphics::highResamplingQuality);
        if (an.span <= 0.0f) { g.drawImageTransformed (im, place (an.shown), false); return; }
        const int n = jlimit (4, 16, (int) std::ceil (an.span / 3.0f) + 1);
        for (int k = 0; k < n; ++k)
        {
            g.setOpacity (1.0f / (float) (k + 1));
            g.drawImageTransformed (im, place (an.shown - an.dir * an.span * (float) k / (float) (n - 1)), false);
        }
    }

    // écran ambre dans la vitre encastrée : plage + état, courbe de réponse, fréquence centrale, Q / BOOST, course de la pédale
    void drawScreen (Graphics& g)
    {
        const auto sc = r (kScreen);
        Graphics::ScopedSaveState ss (g);
        { Path clip; clip.addRoundedRectangle (sc, kScreenRadius * s); g.reduceClipRegion (clip); }
        auto st = proc.currentSettings();
        const float pos = jlimit (0.0f, 1.0f, drawnPedal);
        const float alpha = drawnOn ? 1.0f : 0.42f;
        const float gh = sc.getHeight(), M = 13.0f * s;
        const float X0 = sc.getX() + M, X1 = sc.getRight() - M;

        // ligne du haut : plage + état
        g.setFont (font (tfBold, 13.0f * s));
        g.setColour (kAmber.withAlpha (jmax (alpha, 0.6f)));
        const Rectangle<float> top (X0, sc.getY() + 0.085f * gh - 9.0f * s, X1 - X0, 18.0f * s);
        g.drawText ("RANGE " + String (drawnRange + 1) + "  " + crycat::range (drawnRange).label, top, Justification::centredLeft);
        String state = drawnOn ? "ON" : "BYPASS";
        if (drawnAuto && param ("active")) state = drawnOn ? "AUTO ON" : "AUTO";
        g.drawText (state, top, Justification::centredRight);
        g.setColour (Colour (0xff462e10));
        g.fillRect (X0, sc.getY() + 0.15f * gh, X1 - X0, jmax (1.0f, 0.5f * s));

        // courbe de réponse : 80 Hz .. 5 kHz (log), -24 .. +24 dB
        const auto plot = Rectangle<float>::leftTopRightBottom (X0, sc.getY() + 0.19f * gh, X1, sc.getY() + 0.52f * gh);
        const float f0 = 80.0f, f1 = 5000.0f, dbMax = 24.0f;
        auto xOf = [&] (float f) { return plot.getX() + plot.getWidth() * std::log (f / f0) / std::log (f1 / f0); };
        auto yOf = [&] (float db) { return plot.getCentreY() - plot.getHeight() * 0.5f * jlimit (-1.0f, 1.0f, db / dbMax); };
        {
            const auto& rg = crycat::range (drawnRange);
            g.setColour (kAmber.withAlpha (0.07f * alpha + 0.03f));
            g.fillRect (Rectangle<float>::leftTopRightBottom (xOf (rg.fLo), plot.getY(), xOf (rg.fHi), plot.getBottom()));
            g.setColour (Colour (0xff3c280e));
            g.fillRect (plot.getX(), yOf (0.0f), plot.getWidth(), jmax (1.0f, 0.5f * s));
            for (float f : { 100.0f, 1000.0f }) g.fillRect (xOf (f), plot.getY(), jmax (1.0f, 0.5f * s), plot.getHeight());
            Path curve, fill;
            const int np = 90;
            for (int i = 0; i <= np; ++i)
            {
                const float f = f0 * std::pow (f1 / f0, (float) i / (float) np);
                const float x = xOf (f), y = yOf (crycat::magnitudeDb (st, pos, f));
                if (i == 0) { curve.startNewSubPath (x, y); fill.startNewSubPath (x, plot.getBottom()); }
                else curve.lineTo (x, y);
                fill.lineTo (x, y);
            }
            fill.lineTo (plot.getRight(), plot.getBottom()); fill.closeSubPath();
            g.setColour (Colour (0xff462808).withMultipliedAlpha (alpha));
            g.fillPath (fill);
            g.setColour (kAmberHi.withAlpha (0.95f * alpha));
            g.strokePath (curve, PathStrokeType (1.4f * s, PathStrokeType::curved, PathStrokeType::rounded));
            const float fc = crycat::centreHz (drawnRange, pos);
            const float xc = xOf (fc), yc = yOf (crycat::magnitudeDb (st, pos, fc));
            g.setColour (kAmberHi.withAlpha (alpha));
            g.fillEllipse (xc - 2.6f * s, yc - 2.6f * s, 5.2f * s, 5.2f * s);
        }

        // fréquence centrale en grand + Q / BOOST
        {
            const float fc = crycat::centreHz (drawnRange, pos);
            g.setFont (font (tfBold, 29.0f * s));
            g.setColour (Colour (0xfffff1dc).withAlpha (alpha));
            const String txt = fc >= 1000.0f ? String (fc / 1000.0f, 2) + " kHz" : String (roundToInt (fc)) + " Hz";
            g.drawText (txt, Rectangle<float> (X0, sc.getY() + 0.635f * gh - 22.0f * s, X1 - X0, 44.0f * s), Justification::centred);
            g.setFont (font (tfMed, 11.0f * s));
            g.setColour (kAmber.withAlpha (alpha));
            g.drawText ("Q " + String (crycat::effectiveQ (st.q, pos), 1) + "  \xc2\xb7  BOOST +" + String (st.boost * 15.0f, 1) + " dB",
                        Rectangle<float> (X0, sc.getY() + 0.75f * gh - 9.0f * s, X1 - X0, 18.0f * s), Justification::centred);
        }

        // course de la pédale : barres du talon (gauche) à la pointe (droite)
        const int nb = 16;
        const float bw = (X1 - X0) / (float) nb, by = sc.getBottom() - 11.0f * s;
        for (int i = 0; i < nb; ++i)
        {
            const float t = ((float) i + 0.5f) / (float) nb;
            const float hh = (4.5f + 10.5f * t) * s;
            const bool lit = t <= pos + 0.001f;
            g.setColour (lit ? kAmber.withAlpha (alpha) : Colour (0xff32200a));
            g.fillRect (X0 + (float) i * bw, by - hh, bw - 2.5f * s, hh);
        }
    }

    // ------------------------------------------------------------ pastille : barre de presets, remplacée par la ligne d'état
    String presetName() const { return CrycatProcessor::factory (proc.getCurrentFactory()).name; }
    void stepPreset (int d)
    {
        const int n = CrycatProcessor::kNumFactory;
        proc.loadFactory ((proc.getCurrentFactory() + d + n) % n);
        statusUntil = 0.0;
    }
    void drawPill (Graphics& g)
    {
        const auto pr = r (kPill);
        g.setColour (Colour (0xf0080707));
        g.fillRoundedRectangle (pr, pr.getHeight() * 0.5f);
        g.setColour (Colour (0xc8787674));
        g.drawRoundedRectangle (pr.reduced (0.5f * s), pr.getHeight() * 0.5f, jmax (1.0f, 0.5f * s));
        g.setFont (font (tfMed, 20.0f * s));
        const float sa = jlimit (0.0f, 1.0f, statusAlpha);
        if (sa < 0.999f)
        {
            g.setColour (Colour (0xffeceae8).withAlpha (1.0f - sa));
            g.drawFittedText (presetName(), pr.reduced (36.0f * s, 0).toNearestInt(), Justification::centred, 1, 0.7f);
            for (int side = 0; side < 2; ++side)
            {
                const float cx = side == 0 ? pr.getX() + 17.0f * s : pr.getRight() - 17.0f * s, cy = pr.getCentreY(), t = 5.5f * s;
                const bool hov = pillHover == side + 1;
                Path tri;
                if (side == 0) tri.addTriangle (cx + t * 0.5f, cy - t, cx + t * 0.5f, cy + t, cx - t * 0.9f, cy);
                else           tri.addTriangle (cx - t * 0.5f, cy - t, cx - t * 0.5f, cy + t, cx + t * 0.9f, cy);
                g.setColour ((hov ? Colours::white : Colour (0xffa09e9c)).withAlpha (1.0f - sa));
                g.fillPath (tri);
            }
        }
        if (sa > 0.001f)
        {
            g.setColour (Colour (0xffeceae8).withAlpha (sa));
            g.drawFittedText (drawnStatus, pr.reduced (pr.getHeight() * 0.5f, 0).toNearestInt(), Justification::centred, 1, 0.6f);
        }
    }

    String statusText() const
    {
        if (proc.isCalibrating()) return "CALIBRATION: sweep the pedal heel <-> toe";
        const int lt = proc.learnTarget.load();
        if (lt >= 0) return String ("MIDI LEARN: move a control for ") + CrycatProcessor::learnDef (lt).name;
        if (Time::getMillisecondCounterHiRes() < learnMsgUntil) return learnMsg;      // "<Commande> = CC n" pendant 2 s
        auto pc = [this] (const char* id) { return String (roundToInt (proc.apvts.getParameter (id)->getValue() * 100.0f)) + " %"; };
        return "PEDAL " + String (roundToInt (proc.getPedalShown() * 100.0f)) + " %"
             + "  \xc2\xb7  Q " + pc ("q") + "  \xc2\xb7  PURR " + pc ("purr") + "  \xc2\xb7  BOOST " + pc ("boost");
    }

    void timerCallback() override
    {
        const double now = Time::getMillisecondCounterHiRes();
        auto* ed = findParentComponentOfClass<CrycatEditor>();
        if (ed != nullptr) ed->checkRenderer();          // fenêtre hôte recréée, ou au plus 1 fois par seconde

        // caches : refaits ici seulement (jamais dans paint), après stabilisation de la taille ou changement d'échelle
        if (resizeSettle > 0 && --resizeSettle == 0) rebuildCaches();
        else if (resizeSettle == 0 && now - lastScaleCheckMs > 250.0)
        {
            lastScaleCheckMs = now;
            const float sc = physScale(), ap = (float) Component::getApproximateScaleFactorForComponent (this);
            if (std::abs (sc - dispScale) > 0.01f || std::abs (ap - approxScale) > 0.01f) { dispScale = sc; approxScale = ap; rebuildCaches(); }
        }

        // chien de garde : un redessin demandé n'arrive pas -> on relance le moteur de rendu et on redessine tout
        if (repaintAskedMs > 0.0 && isShowing() && now - repaintAskedMs > 1500.0 && lastPaintMs < repaintAskedMs)
        {
            repaintAskedMs = 0.0;
            if (ed != nullptr) ed->resetRenderer();
            repaint();
        }

        proc.pollCalibration();
        // anti-gel : positions du plateau précalculées au fil des ticks (budget de quelques ms), jamais dans paint
        if (getWidth() > 0 && resizeSettle == 0)
        {
            const int cur = roundToInt (jlimit (0.0f, 1.0f, proc.getPedalShown()) * (float) (kFrames - 1));
            const double t0 = Time::getMillisecondCounterHiRes();
            bool built = false;
            while (Time::getMillisecondCounterHiRes() - t0 < 6.0 && treadle.buildNextMissing (cur)) built = true;
            if (built) askRepaint (r (treadle.designBounds()).toNearestInt().expanded (2));
        }

        // MIDI Learn : confirmation 2 s dans la ligne d'état
        const int learned = proc.lastLearned.exchange (-1);
        if (learned >= 0)
        {
            learnMsg = String (CrycatProcessor::learnDef (learned).name) + " = " + proc.learnAssignText (learned);
            learnMsgUntil = now + 2000.0;
        }

        const int rg = currentRange();
        const bool autoM = param ("auto"), on = proc.isEffectOn(), armed = autoM && param ("active");
        const float ped = proc.getPedalShown();
        bool screen = false, moved = false;

        if (std::abs (ped - drawnPedal) > 0.002f)
        {
            if (drawnPedal >= 0.0f) moved = true;
            drawnPedal = ped; screen = true;
            askRepaint (r (treadle.designBounds()).toNearestInt().expanded (2));
        }
        if (rg != drawnRange)
        {
            if (drawnRange >= 0) moved = true;
            const float h = kKnobR + 34.0f;
            askRepaint (r (Rectangle<float> (kKnob.x - h, kKnob.y - h, 2 * h, 2 * h)).toNearestInt().expanded (2));
            drawnRange = rg; screen = true;
        }
        if (rangeAnim.step (rangeAngleDeg (rg)))
            askRepaint (r (Rectangle<float> (kKnob.x - kKnobImg * 0.5f, kKnob.y - kKnobImg * 0.5f, kKnobImg, kKnobImg)).toNearestInt().expanded (2));
        if (drawnAuto != autoM && drawnStarted) toggleMidUntil = now + 55.0;
        if (autoM != drawnAuto || on != drawnOn || armed != drawnArmed)
        {
            if (drawnStarted) moved = true;
            drawnAuto = autoM; drawnOn = on; drawnArmed = armed; screen = true;
            askRepaint (r (kToggle).toNearestInt().expanded (3));
        }
        drawnStarted = true;
        const bool toggleMoving = now < toggleMidUntil;
        if (toggleMoving != drawnToggleMoving) { drawnToggleMoving = toggleMoving; askRepaint (r (kToggle).toNearestInt().expanded (3)); }
        // LED (comme Echoflex) : allumage / extinction en fondu (0.45 / 0.28 par image) ; veille AUTO = faible lueur
        const float ledTarget = on ? 1.0f : (armed ? 0.10f : 0.0f);
        ledLevel += (ledTarget - ledLevel) * (ledTarget > ledLevel ? 0.45f : 0.28f);
        if (std::abs (ledLevel - ledTarget) < 0.003f) ledLevel = ledTarget;
        if (std::abs (ledLevel - drawnLed) > 0.003f)
        {
            drawnLed = ledLevel;
            askRepaint (r (kLedGlow).toNearestInt().expanded (2));
            askRepaint (r (kFs).toNearestInt().expanded (2));
        }
        for (int i = 0; i < 3; ++i)
        {
            const float v = proc.apvts.getParameter (kSmallId[i])->getValue();
            if (std::abs (v - drawnSmall[i]) > 0.002f)
            {
                if (drawnSmall[i] >= 0.0f) moved = true;
                drawnSmall[i] = v; screen = true;      // Q et BOOST changent la courbe
            }
            if (smallAnim[i].step (-135.0f + 270.0f * drawnSmall[i]))
                askRepaint (r (Rectangle<float> (kSmall[i].x - kSmallImg * 0.5f, kSmall[i].y - kSmallImg * 0.5f, kSmallImg, kSmallImg)).toNearestInt().expanded (2));
        }
        if (screen) askRepaint (r (kScreen).toNearestInt().expanded (2));

        // pastille : la ligne d'état prend la place des presets pendant les réglages (fondu ~120 ms), puis s'efface (~300 ms)
        const String st = statusText();
        const bool special = proc.learnTarget.load() >= 0 || proc.isCalibrating() || now < learnMsgUntil;
        if (moved || special) statusUntil = now + 2500.0;
        const float target = (now < statusUntil) ? 1.0f : 0.0f;
        statusAlpha += (target - statusAlpha) * (target > statusAlpha ? 0.45f : 0.11f);
        if (std::abs (statusAlpha - target) < 0.004f) statusAlpha = target;
        const int fac = proc.getCurrentFactory();
        if (st != drawnStatus || std::abs (statusAlpha - drawnStatusAlpha) > 0.003f || fac != drawnFactory)
        {
            drawnStatus = st; drawnStatusAlpha = statusAlpha; drawnFactory = fac;
            askRepaint (r (kPill).toNearestInt().expanded (2));
        }
    }

    // ------------------------------------------------------------ menus (style Octopus, ouverts là où l'on clique)
    void showPresetMenu()
    {
        PopupMenu m, rgs;
        m.setLookAndFeel (&menuLnf);
        NineHandsMenu::addHeader (m, menuLnf.f, NineHandsMenu::icoPreset, NineHandsMenu::kAccent, "Presets", presetName());
        const int cur = proc.getCurrentFactory();
        for (int i = 0; i < CrycatProcessor::kNumFactory; ++i)
            m.addItem (101 + i, String (i + 1) + ". " + CrycatProcessor::factory (i).name, true, i == cur);
        m.addSeparator();
        const int cr = currentRange();
        for (int i = 0; i < crycat::kNumRanges; ++i) rgs.addItem (1 + i, crycat::range (i).name, true, i == cr);
        m.addSubMenu ("Sweep range", rgs);
        Component::SafePointer<PedalView> sp (this);
        m.showMenuAsync (PopupMenu::Options().withMousePosition(), [sp] (int res)
        {
            if (sp == nullptr || res == 0) return;
            if (res >= 101) { sp->proc.loadFactory (res - 101); sp->statusUntil = 0.0; }
            else sp->proc.setParamValue ("range", (float) (res - 1));
        });
    }

    // commande sous la souris (même ordre de test que mouseDown) : index MIDI Learn, -1 = hors commande
    int learnIndexAt (Point<float> p) const
    {
        if (kScreen.contains (p) || kPill.contains (p)) return -1;
        for (int i = 0; i < crycat::kNumRanges; ++i)
            if (p.getDistanceFrom (rangeNumberPos (i)) < 11.0f) return CrycatProcessor::lRange;
        if (p.getDistanceFrom (kKnob) < kKnobR * 1.1f) return CrycatProcessor::lRange;
        for (int i = 0; i < 3; ++i)
            if (p.getDistanceFrom (kSmall[i]) < kSmallR * 1.15f) return CrycatProcessor::lQ + i;
        if (kToggleHit.contains (p)) return CrycatProcessor::lAuto;
        if (kFsC.getDistanceFrom (p) < kFsHitR * 1.2f) return CrycatProcessor::lFs;
        if (kPlate.contains (p)) return CrycatProcessor::lPedal;
        return -1;
    }

    void addLearnSection (PopupMenu& m, int i)
    {
        const String name = CrycatProcessor::learnDef (i).name;
        const int lt = proc.learnTarget.load();
        m.addItem (1000 + i, "MIDI Learn: " + name + " (" + proc.learnAssignText (i) + ")", true, lt == i);
        m.addItem (1100 + i, "Clear MIDI: " + name, proc.learnAssignText (i) != "none");
        if (lt >= 0) m.addItem (1200, "Cancel MIDI learn");
        m.addSeparator();
    }

    void addMidiSubmenu (PopupMenu& m)
    {
        PopupMenu midi;
        for (int i = 0; i < CrycatProcessor::numLearn; ++i)
            midi.addItem (1000 + i, String ("Learn: ") + CrycatProcessor::learnDef (i).name + " (" + proc.learnAssignText (i) + ")",
                          true, proc.learnTarget.load() == i);
        midi.addSeparator();
        if (proc.learnTarget.load() >= 0) midi.addItem (1200, "Cancel MIDI learn");
        midi.addItem (1201, "Clear all MIDI assignments");
        midi.addSeparator();
        midi.addItem (1202, "MAN / AUTO and footswitch also learn a MIDI note", false);
        m.addSubMenu ("MIDI", midi);
    }

    void handleLearnChoice (int r)
    {
        if (r >= 1000 && r < 1000 + CrycatProcessor::numLearn)          // re-cliquer sur la commande en attente annule
            proc.learnTarget.store (proc.learnTarget.load() == r - 1000 ? -1 : r - 1000);
        else if (r >= 1100 && r < 1100 + CrycatProcessor::numLearn) proc.clearLearn (r - 1100);
        else if (r == 1200) proc.learnTarget.store (-1);
        else if (r == 1201) proc.clearMidiMap();
    }

    void showMenu (Point<float> p)
    {
        auto* ed = findParentComponentOfClass<CrycatEditor>();
        PopupMenu m;
        m.setLookAndFeel (&menuLnf);
        const int learnIdx = learnIndexAt (p);
        if (learnIdx >= 0)
        {
            const int ico = learnIdx == CrycatProcessor::lPedal ? NineHandsMenu::icoPedal
                          : (learnIdx == CrycatProcessor::lAuto || learnIdx == CrycatProcessor::lFs) ? NineHandsMenu::icoSwitch : NineHandsMenu::icoKnob;
            NineHandsMenu::addHeader (m, menuLnf.f, ico, NineHandsMenu::kAccent, CrycatProcessor::learnDef (learnIdx).name,
                                      "MIDI: " + proc.learnAssignText (learnIdx));
            addLearnSection (m, learnIdx);
        }
        else
            NineHandsMenu::addHeader (m, menuLnf.f, NineHandsMenu::icoPedal, NineHandsMenu::kAccent, "Crycat",
                                      "Vocal wah  v" + String (JucePlugin_VersionString));
        const bool onFs = learnIdx == CrycatProcessor::lFs;
        const bool onToggle = learnIdx == CrycatProcessor::lAuto;
        if (onFs || onToggle)
        {
            m.addSectionHeader ("MIDI switch messages");
            m.addItem (41, "Momentary (each press toggles)", true, ! param ("latch"));
            m.addItem (42, "Latching (127 = ON, 0 = OFF)", true, param ("latch"));
            m.addSeparator();
        }
        else if (learnIdx < 0 || learnIdx == CrycatProcessor::lPedal)
        {
            m.addSectionHeader ("Expression pedal");
            m.addItem (35, "Calibrate (sweep heel <-> toe for 6 s)  -  " + proc.calibrationDescription());
            m.addItem (34, "Reset pedal calibration");
            m.addItem (33, "Invert pedal direction", true, param ("invert"));
            PopupMenu glide;
            const float gl = proc.apvts.getRawParameterValue ("smooth")->load();
            for (int i = 0; i < 6; ++i) { const int ms[6] = { 0, 8, 15, 30, 60, 120 }; glide.addItem (61 + i, String (ms[i]) + " ms", true, std::abs (gl - (float) ms[i]) < 1.0f); }
            m.addSubMenu ("Pedal glide (smoothing)", glide);
            m.addSeparator();
            m.addSectionHeader ("Auto-engage");
            PopupMenu rel;
            const float ao = proc.apvts.getRawParameterValue ("autooff")->load();
            for (int i = 0; i < 5; ++i) { const int ms[5] = { 150, 300, 400, 800, 1500 }; rel.addItem (71 + i, String (ms[i]) + " ms", true, std::abs (ao - (float) ms[i]) < 1.0f); }
            m.addSubMenu ("Switch off after resting on the heel", rel);
            m.addItem (53, "Respond to MIDI Program Change (PC 1-10)", true, param ("pc"));
            m.addSeparator();
        }
        if (learnIdx < 0) addMidiSubmenu (m);
        PopupMenu sizes, glowM;
        addSizeItems (sizes, ed);
        m.addSubMenu ("Plugin size", sizes);
        {
            const int nowPc = roundToInt (glow * 100.0f);
            for (int i = 0; i < NineHandsGlow::numSteps; ++i)
            {
                const int pc = NineHandsGlow::steps[i];
                glowM.addItem (81 + i, "Glow " + String (pc) + " %" + (pc == 100 ? "  (default)" : ""), true, nowPc == pc);
            }
        }
        m.addSubMenu ("Glow (halo of the lights)", glowM);

        Component::SafePointer<PedalView> sp (this);
        m.showMenuAsync (PopupMenu::Options().withMousePosition(), [sp] (int res)      // toujours là où l'on clique
        {
            if (sp == nullptr || res == 0) return;
            auto& pr = sp->proc;
            const int glideMs[6] = { 0, 8, 15, 30, 60, 120 }, relMs[5] = { 150, 300, 400, 800, 1500 };
            if (res >= 1000) { sp->handleLearnChoice (res); return; }
            switch (res)
            {
                case 33: pr.togglePedalSwitch ("invert"); break;
                case 34: pr.resetCalibration(); break;
                case 35: pr.startCalibration(); break;
                case 41: pr.setParamValue ("latch", 0.0f); break;
                case 42: pr.setParamValue ("latch", 1.0f); break;
                case 53: pr.togglePedalSwitch ("pc"); break;
                default:
                    if (res >= 61 && res <= 66) pr.setParamValue ("smooth", (float) glideMs[res - 61]);
                    else if (res >= 71 && res <= 75) pr.setParamValue ("autooff", (float) relMs[res - 71]);
                    else if (res >= 81 && res < 81 + NineHandsGlow::numSteps)
                    {
                        const int pc = NineHandsGlow::steps[res - 81];
                        NineHandsGlow::setPercent (JucePlugin_Name, pc);
                        sp->glow = (float) pc / 100.0f;
                        sp->repaint();
                    }
                    else handleSizeChoice (res, sp->findParentComponentOfClass<CrycatEditor>());
                    break;
            }
        });
    }

    CrycatProcessor& proc;
    ScaledCache bg, fsRefl, ledOn, ledGlow, tg[3];
    Image markerSrc, markerBig, markerSmall, print;
    TreadleWarp treadle;
    Typeface::Ptr tfReg, tfMed, tfBold;
    std::unique_ptr<Drawable> cryLogo;
    NineHandsMenu::MenuLnf menuLnf;
    float s = kDefaultScale * kRefH / (float) kH;
    float glow = 1.0f;                     // réglage Glow (1 = 100 %)

    // anti-gel v2 : échelle d'affichage, stabilisation après redimensionnement, suivi des redessins
    float dispScale = 1.0f, approxScale = 1.0f;
    int resizeSettle = 0;
    double lastPaintMs = 0.0, repaintAskedMs = 0.0, lastScaleCheckMs = 0.0;
public:
    void initCaches() { dispScale = physScale(); approxScale = (float) Component::getApproximateScaleFactorForComponent (this); resizeSettle = 0; rebuildCaches(); }
private:

    Drag drag = Drag::None;
    float dragStartY = 0, dragStartVal = 0;
    int dragStartRange = 0, pillHover = 0;
    bool pressed = false, drawnStarted = false, drawnToggleMoving = false;
    double toggleMidUntil = 0.0, statusUntil = 0.0;
    float ledLevel = 0.0f, drawnLed = -1.0f, statusAlpha = 0.0f, drawnStatusAlpha = -1.0f;
    MarkerAnim rangeAnim, smallAnim[3];

    float drawnPedal = -1.0f, drawnSmall[3] = { -1.0f, -1.0f, -1.0f };
    int drawnRange = -1, drawnFactory = -1;
    bool drawnAuto = false, drawnOn = true, drawnArmed = false;
    String drawnStatus;
    String learnMsg;                       // "Q = CC 21" pendant 2 s après un MIDI Learn
    double learnMsgUntil = 0.0;
};

//==============================================================================
CrycatEditor::CrycatEditor (CrycatProcessor& p) : AudioProcessorEditor (&p), proc (p)
{
    view = std::make_unique<PedalView> (proc);
    addAndMakeVisible (*view);
    setResizable (true, true);
    const int minH = (int) std::lround (kRefH * kDefaultScale);          // jamais plus petit que la taille par défaut
    const int maxH = 1120;
    setResizeLimits ((int) std::lround ((double) minH * kW / kH), minH, (int) std::lround ((double) maxH * kW / kH), maxH);
    getConstrainer()->setFixedAspectRatio ((double) kW / (double) kH);
    setOpaque (true);                    // anti-gel : l'hôte ne redessine jamais ce qui est derrière la fenêtre
    // taille d'ouverture : celle enregistrée pour cette instance (projet) si elle existe,
    // sinon celle choisie dans le menu « Default size (new windows) »
    const int saved = jlimit (-1, 2, proc.uiScaleIdx.load());
    if (saved >= 0) setScaleIndex (saved);
    else            applyScaleIndex (WigaWindowSize::defaultIndex (JucePlugin_Name, kNumSizes));
    view->initCaches();
}

CrycatEditor::~CrycatEditor() = default;

//==============================================================================
// Anti-gel de la fenêtre (Windows) : JUCE 8 dessine par défaut avec Direct2D ; avec certains pilotes (Intel)
// la fenêtre cesse de se rafraîchir alors que le DAW continue. Le moteur logiciel est stable partout.
//==============================================================================
// Anti-gel v2 (NINE HANDS | DSP) :
//  1. moteur de rendu logiciel forcé sur Windows (Direct2D peut figer la fenêtre dans certains hôtes),
//     appliqué à chaque nouvelle fenêtre hôte (peer) et revérifié toutes les secondes, jamais en boucle ;
//  2. aucun calcul lourd dans paint() : les caches d'images (fond, commandes, positions du plateau) sont refaits
//     par le timer seulement, après stabilisation de la taille ou quand l'échelle d'affichage change (au plus toutes les 250 ms) ;
//  3. chien de garde : si un redessin demandé n'est pas arrivé au bout de 1,5 s alors que la fenêtre est
//     visible, le moteur de rendu est réappliqué et toute la fenêtre est redessinée ;
//  4. côté audio : aucun appel à l'hôte ni allocation depuis le thread audio (voir PluginProcessor).
void CrycatEditor::useSoftwareRenderer()
{
    auto* peer = getPeer();
    if ((void*) peer != lastPeer) { lastPeer = (void*) peer; repaint(); }
    lastRendererCheckMs = Time::getMillisecondCounterHiRes();
   #if JUCE_WINDOWS
    if (peer != nullptr)
    {
        int sw = peer->getAvailableRenderingEngines().indexOf ("Software Renderer");
        if (sw < 0) sw = 0;
        if (peer->getCurrentRenderingEngine() != sw)
            peer->setCurrentRenderingEngine (sw);
    }
   #endif
}

void CrycatEditor::checkRenderer()
{
    if ((void*) getPeer() != lastPeer || Time::getMillisecondCounterHiRes() - lastRendererCheckMs > 1000.0)
        useSoftwareRenderer();
}

void CrycatEditor::resetRenderer()
{
    lastPeer = nullptr;
    useSoftwareRenderer();
    repaint();
}

void CrycatEditor::paint (Graphics& g) { g.fillAll (Colours::black); }   // la pédale recouvre tout ; fenêtre opaque
void CrycatEditor::parentHierarchyChanged() { useSoftwareRenderer(); }
void CrycatEditor::visibilityChanged()      { useSoftwareRenderer(); if (isShowing()) repaint(); }

void CrycatEditor::resized()
{
    // tolérance de 2 px (mise à l'échelle Windows 125 / 150 %) : les limites du constrainer suffisent, pas de boucle avec l'hôte
    view->setBounds (getLocalBounds());
}

int CrycatEditor::getScaleIndex() const
{
    const float sc = (float) getHeight() / kRefH;
    for (int i = 0; i < 3; ++i) if (std::abs (sc - kScales[i]) < 0.02f) return i;
    return -1;
}

void CrycatEditor::setScaleIndex (int idx)
{
    idx = jlimit (0, 2, idx);
    proc.uiScaleIdx = idx;               // taille choisie pour cette instance (enregistrée avec le projet)
    applyScaleIndex (idx);
}

void CrycatEditor::applyScaleIndex (int idx)
{
    const float sc = kScales[jlimit (0, 2, idx)];
    const int h = (int) std::lround (kRefH * sc);
    setSize ((int) std::lround ((double) h * kW / kH), h);
}

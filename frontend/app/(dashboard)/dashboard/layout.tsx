export default function DashboardLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6">
      {children}
    </div>
  );
}

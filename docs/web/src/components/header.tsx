export function Header({
  headerText,
  description,
}: Readonly<{ headerText: string; description: string }>) {
  return (
    <div className='mx-auto flex max-w-7xl flex-col items-center py-12 pb-10'>
      <h1 className='text-center text-6xl font-bold tracking-tighter leading-[1.1] mb-4'>
        {headerText}
      </h1>
      <h2 className='text-center text-5xl font-semibold tracking-tighter leading-[1.1]'>
        {description}
      </h2>
    </div>
  );
}
